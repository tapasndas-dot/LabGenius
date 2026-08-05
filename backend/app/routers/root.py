from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    return {
        "application": "LabGenius",
        "version": "0.1.0",
        "status": "Running"
    }