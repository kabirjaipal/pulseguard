import time
import datetime
import httpx
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.endpoint import Endpoint
from app.models.monitoring_result import MonitoringResult

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

@celery_app.task(name="app.core.tasks.ping_endpoint_task")
def ping_endpoint_task(endpoint_id: int):
    """
    Performs an HTTP request to the endpoint, records response time and status,
    and saves the results into the MonitoringResult table.
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
                
        except httpx.RequestError as exc:
            # Captures timeouts, connection errors, DNS errors, etc.
            response_time_ms = int((time.time() - start_time) * 1000)
            is_healthy = False
            error_message = f"Network request failed: {str(exc)}"
            
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
        db.commit()
        
        return {
            "endpoint_id": endpoint_id,
            "status_code": status_code,
            "latency_ms": response_time_ms,
            "is_healthy": is_healthy,
            "error": error_message
        }
    except Exception as e:
        db.rollback()
        return f"Error executing check for endpoint {endpoint_id}: {str(e)}"
    finally:
        db.close()
