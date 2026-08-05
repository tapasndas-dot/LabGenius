from fastapi import APIRouter

from app.database.database import supabase

router = APIRouter()


@router.get("/")
async def database_status():
    try:
        response = (
            supabase.table("pg_tables")
            .select("*")
            .limit(1)
            .execute()
        )

        return {
            "status": "connected",
            "message": "Supabase connection successful"
        }

    except Exception as ex:
        return {
            "status": "failed",
            "error": str(ex)
        }