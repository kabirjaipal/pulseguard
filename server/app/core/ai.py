import json
import logging
from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)

def generate_mock_analysis(endpoint, recent_results: list) -> dict:
    """
    Generates a tailored mock AI analysis based on the actual error messages
    to keep local development frictionless if no OpenRouter API key is present.
    """
    last_err = "Unknown connection issue"
    status_code = None
    
    if recent_results:
        # Get details from the latest check result
        last_result = recent_results[0]
        last_err = last_result.error_message or "Connection timed out"
        status_code = last_result.status_code

    if status_code:
        summary = (
            f"The monitored API endpoint '{endpoint.name}' is returning HTTP status code {status_code} repeatedly. "
            f"This demonstrates that the application host is online, but the backend server encountered an error while processing the request."
        )
        suggestions = (
            f"- Inspect the application logs on the target server to debug the internal HTTP {status_code} error.\n"
            f"- Double-check if the request method ({endpoint.method}) is fully supported by the route.\n"
            f"- Verify that the backend database, cache layer, or internal API dependencies are fully operational."
        )
    else:
        summary = (
            f"The monitoring agent failed to connect to '{endpoint.url}' due to a connection failure: '{last_err}'. "
            f"This indicates that the target server is either completely offline, experiencing heavy network loss, or blocking incoming ping requests."
        )
        suggestions = (
            f"- Check if the target server host is active and listening for network traffic.\n"
            f"- Inspect firewall rules, DNS records, and security groups to ensure incoming connections are not blocked.\n"
            f"- Test network routing to '{endpoint.url}' using standard diagnostics like ping or traceroute."
        )
        
    return {
        "summary": summary,
        "suggestions": suggestions
    }

def generate_incident_analysis(endpoint, recent_results: list) -> dict:
    """
    Queries the OpenRouter API using the Groq SDK to analyze recent endpoint ping failures and determine the root cause.
    Uses JSON mode to guarantee a structured response.
    """
    if not settings.OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set. Falling back to local mock AI analysis.")
        return generate_mock_analysis(endpoint, recent_results)

    try:
        # Initialize the Groq SDK client pointing to OpenRouter
        client = Groq(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY
        )
        
        # 1. Format logs for the LLM
        logs_summary = []
        for res in recent_results[:5]: # Take last 5 attempts
            logs_summary.append({
                "status_code": res.status_code,
                "latency_ms": res.response_time_ms,
                "is_healthy": res.is_healthy,
                "error_message": res.error_message,
                "checked_at": res.checked_at.isoformat() if res.checked_at else None
            })
            
        logs_json = json.dumps(logs_summary, indent=2)

        # 2. Build system and user prompts
        system_prompt = (
            "You are PulseGuard AI, an expert API monitoring and automated devops analysis platform.\n"
            "Analyze the recent failed API logs provided by the user and diagnose the likely root cause.\n"
            "You MUST respond ONLY with a valid JSON object containing exactly these keys:\n"
            "- 'summary': A 2-3 sentence overview of the root cause and any pattern detected in the failures.\n"
            "- 'suggestions': A bulleted list of 3-4 actionable troubleshooting recommendations to fix the issue.\n"
            "Do not include any intro, outro, or markdown text. Only return the JSON object."
        )

        user_prompt = (
            f"Monitored Endpoint:\n"
            f"- Name: {endpoint.name}\n"
            f"- URL: {endpoint.url}\n"
            f"- Method: {endpoint.method}\n\n"
            f"Recent Failed Logs:\n"
            f"{logs_json}\n\n"
            f"Analyze the failures and provide the JSON report:"
        )

        # 3. Request LLM completion using Groq SDK with OpenRouter custom headers
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=settings.AI_MODEL,
            response_format={"type": "json_object"},
            temperature=0.2, # Lower temperature for analytical accuracy
            max_tokens=500,
            extra_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "PulseGuard"
            }
        )

        response_text = chat_completion.choices[0].message.content
        result = json.loads(response_text)
        
        # Ensure we have both keys
        if "summary" in result and "suggestions" in result:
            return result
        else:
            raise ValueError("OpenRouter JSON response missing required fields.")
            
    except Exception as e:
        logger.error("Error calling OpenRouter via Groq SDK: %s. Falling back to mock analysis.", str(e), exc_info=True)
        return generate_mock_analysis(endpoint, recent_results)

