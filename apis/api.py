
from fastapi import APIRouter
from .routes.student.login import router as login_router
from .routes.course.course import router as course_router
from .routes.course_order.course_order import router as course_order_router

from .routes.cron.sync_to_mongo import router as cron_router
from .routes.teacher.teachers import router as teacherRouter
router = APIRouter()
router.include_router(login_router)
router.include_router(course_router)
router.include_router(course_order_router)
router.include_router(cron_router)
router.include_router(teacherRouter)