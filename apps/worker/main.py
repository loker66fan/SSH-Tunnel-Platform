
import asyncio
from core.logger import logger
from infra.queue.memory import task_queue
from modules.tunnel.manager import tunnel_manager
from modules.audit.logger import audit_logger
from modules.audit.models import AuditLog

async def process_tasks():
    logger.info("Worker task processor started")
    while True:
        task = await task_queue.get()
        task_id = task.get("task_id")
        task_type = task.get("type")
        user = task.get("user")
        config = task.get("config")
        
        logger.info(f"Processing task {task_id} of type {task_type}")
        
        try:
            if task_type == "create_tunnel":
                tid = await tunnel_manager.create_local_forward(
                    config['ssh_host'], config['ssh_port'], 
                    config['username'], config['password'],
                    config['local_port'], config['remote_host'], config['remote_port']
                )
                logger.info(f"Successfully created tunnel {tid} for task {task_id}")
                
                await audit_logger.log(AuditLog(
                    user=user,
                    action="create_tunnel_execution",
                    resource=f"{config['remote_host']}:{config['remote_port']}",
                    status="success",
                    details=f"Task ID: {task_id}, Tunnel ID: {tid}"
                ))
            elif task_type == "stop_tunnel":
                tunnel_id = task.get("tunnel_id")
                success = await tunnel_manager.stop_tunnel(tunnel_id)
                status = "success" if success else "failed"
                await audit_logger.log(AuditLog(
                    user=user,
                    action="stop_tunnel_execution",
                    resource=tunnel_id,
                    status=status,
                    details=f"Task ID: {task_id}"
                ))
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            await audit_logger.log(AuditLog(
                user=user,
                action=f"{task_type}_execution",
                resource=str(config.get('remote_host')) if config else "unknown",
                status="failed",
                details=f"Task ID: {task_id}, Error: {str(e)}"
            ))
        finally:
            task_queue.task_done()

async def main():
    logger.info("Worker starting...")
    # In a real distributed system, this process would be separate.
    # For MVP, we'll run it alongside the API or as a separate process
    # that shares the memory queue (if using a real MQ, it would be truly separate).
    # Since we use a memory queue, this MUST run in the same process as the API
    # OR we use a real MQ like Redis.
    await process_tasks()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped")
