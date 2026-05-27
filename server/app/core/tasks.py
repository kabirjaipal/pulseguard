import time
import datetime
import json
import httpx
from celery.exceptions import MaxRetriesExceededError
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.endpoint import Endpoint
from app.models.monitoring_result import MonitoringResult
from app.models.incident_analysis import IncidentAnalysis
from app.core.notifications import dispatch_alert
from app.core.redis_client import redis_client
from app.core.ai import generate_incident_analysis

@celery_app.task(name="app.core.tasks.scheduler_task")
def scheduler_task():
    """
    Periodically checks the database for active endpoints that are due to be pinged,
    spawns a ping task for each, and updates their last_checked_at timestamp.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 1. Fetch all active endpoints
        active_endpoints = db.query(Endpoint).filter(Endpoint.is_active == True).all()
        
        due_endpoints = []
        for endpoint in active_endpoints:
            # If the endpoint has never been checked, it is due immediately.
            if endpoint.last_checked_at is None:
                due_endpoints.append(endpoint)
            else:
                # If elapsed time exceeds check_interval, it is due.
                time_elapsed = now - endpoint.last_checked_at
                if time_elapsed >= datetime.timedelta(seconds=endpoint.check_interval):
                    due_endpoints.append(endpoint)
                    
        # 2. Dispatch due endpoints and mark them as scheduled
        for endpoint in due_endpoints:
            # We set last_checked_at to 'now' immediately to prevent the scheduler
            # from launching another ping in the next beat tick before this one completes.
            endpoint.last_checked_at = now
            db.add(endpoint)
            
            # Dispatch the ping task asynchronously to celery workers
            ping_endpoint_task.delay(endpoint.id)
            
        db.commit()
        return f"Scheduled {len(due_endpoints)} endpoints for checking."
    except Exception as e:
        db.rollback()
        return f"Error in scheduler_task: {str(e)}"
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, name="app.core.tasks.ping_endpoint_task")
def ping_endpoint_task(self, endpoint_id: int):
    """
    Performs an HTTP request to the endpoint, records response time and status,
    and saves the results into the MonitoringResult table.
    Retries up to 3 times on transient failures/timeouts with a 5-second delay.
    """
    db = SessionLocal()
    try:
        # 1. Fetch the endpoint metadata
        endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
        if not endpoint:
            return f"Endpoint {endpoint_id} not found."
            
        start_time = time.time()
        status_code = None
        response_time_ms = None
        is_healthy = False
        error_message = None
        
        # 2. Perform the HTTP request
        try:
            # We use httpx client with a 10s timeout to ping the endpoint URL
            response = httpx.request(
                method=endpoint.method,
                url=endpoint.url,
                timeout=10.0
            )
            
            # Compute latency in milliseconds
            response_time_ms = int((time.time() - start_time) * 1000)
            status_code = response.status_code
            
            # Health check: classify status codes in the 2xx range as healthy
            if 200 <= status_code < 300:
                is_healthy = True
            else:
                error_message = f"Non-2xx status code returned: {status_code}"
                # Retry for transient application/server errors (e.g. 500, 503)
                try:
                    raise self.retry(countdown=5)
                except MaxRetriesExceededError:
                    pass # Out of retries, mark as unhealthy
                
        except httpx.RequestError as exc:
            # Captures timeouts, connection errors, DNS errors, etc.
            try:
                raise self.retry(exc=exc, countdown=5)
            except MaxRetriesExceededError:
                response_time_ms = int((time.time() - start_time) * 1000)
                is_healthy = False
                error_message = f"Network request failed after retries: {str(exc)}"
            
        except Exception as exc:
            response_time_ms = int((time.time() - start_time) * 1000)
            is_healthy = False
            error_message = f"Unexpected error during ping: {str(exc)}"
            
        # 3. Save result log to database
        result = MonitoringResult(
            endpoint_id=endpoint.id,
            status_code=status_code,
            response_time_ms=response_time_ms,
            is_healthy=is_healthy,
            error_message=error_message
        )
        db.add(result)
        
        # 4. State transition and notifications
        project = endpoint.project
        owner = project.owner
        ai_analysis_payload = None
        
        if is_healthy:
            # Recovery: was failing, now healthy
            if endpoint.status == "failing":
                endpoint.status = "healthy"
                endpoint.consecutive_failures = 0
                dispatch_alert(endpoint, project, owner, is_recovery=True)
            else:
                endpoint.consecutive_failures = 0
        else:
            # Failure increment
            endpoint.consecutive_failures += 1
            # Alert on transition from healthy to failing
            if endpoint.consecutive_failures >= 3 and endpoint.status == "healthy":
                endpoint.status = "failing"
                
                # Fetch recent failed results to send to AI
                recent_failures = db.query(MonitoringResult).filter(
                    MonitoringResult.endpoint_id == endpoint.id,
                    MonitoringResult.is_healthy == False
                ).order_by(MonitoringResult.checked_at.desc()).limit(5).all()
                
                # Generate AI Incident Analysis
                ai_analysis = generate_incident_analysis(endpoint, recent_failures)
                ai_analysis_payload = ai_analysis
                
                # Save the AI incident analysis to the database
                analysis_log = IncidentAnalysis(
                    endpoint_id=endpoint.id,
                    summary=ai_analysis.get("summary", "No summary generated"),
                    suggestions=ai_analysis.get("suggestions", "No suggestions generated"),
                    raw_logs=json.dumps([
                        {
                            "status_code": r.status_code,
                            "latency_ms": r.response_time_ms,
                            "is_healthy": r.is_healthy,
                            "error_message": r.error_message,
                            "checked_at": r.checked_at.isoformat() if r.checked_at else None
                        } for r in recent_failures
                    ])
                )
                db.add(analysis_log)
                
                # Dispatch alert notification with the AI analysis summary embedded
                dispatch_alert(
                    endpoint=endpoint,
                    project=project,
                    owner=owner,
                    is_recovery=False,
                    error_message=error_message,
                    ai_analysis=ai_analysis
                )
                
        db.add(endpoint)
        db.commit()
        
        # Cache the latest result in Redis as a JSON string
        cache_payload = {}
        try:
            cache_payload = {
                "id": result.id,
                "endpoint_id": endpoint.id,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "is_healthy": is_healthy,
                "error_message": error_message,
                "checked_at": result.checked_at.isoformat() if result.checked_at else datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            # Set TTL to 2x check_interval (minimum 120s)
            expire_seconds = max(endpoint.check_interval * 2, 120)
            redis_client.setex(
                f"endpoint:{endpoint.id}:latest",
                expire_seconds,
                json.dumps(cache_payload)
            )
        except Exception as cache_err:
            # Log cache failures to console without failing the ping task execution
            print(f"Error writing to Redis cache for endpoint {endpoint.id}: {str(cache_err)}")
        
        # Publish live WebSocket update via Redis Pub/Sub
        try:
            pubsub_payload = {
                "type": "endpoint_update",
                "owner_id": owner.id,
                "project_id": project.id,
                "endpoint_id": endpoint.id,
                "status": endpoint.status,
                "consecutive_failures": endpoint.consecutive_failures,
                "latest_result": cache_payload,
                "ai_analysis": ai_analysis_payload
            }
            redis_client.publish("pulseguard_updates", json.dumps(pubsub_payload))
        except Exception as pub_err:
            print(f"Error publishing update to Redis Pub/Sub channel: {str(pub_err)}")
            
        return {
            "endpoint_id": endpoint_id,
            "status_code": status_code,
            "latency_ms": response_time_ms,
            "is_healthy": is_healthy,
            "status": endpoint.status,
            "consecutive_failures": endpoint.consecutive_failures,
            "error": error_message
        }
    except Exception as e:
        db.rollback()
        return f"Error executing check for endpoint {endpoint_id}: {str(e)}"
    finally:
        db.close()
