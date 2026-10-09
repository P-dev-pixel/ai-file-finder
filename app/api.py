from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query  # type: ignore[import-not-found]

import sqlite3
from pathlib import Path

from pydantic import BaseModel
from app.main import index_folder



from app.database import(
    initialize_database,
    search_files,
    get_search_roots,
    add_search_root
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield
    
app = FastAPI(
    title="AI File Finder API",
    description="API for searching and indexing local files.",
    version="3.0.0",
    lifespan=lifespan,
)

class IndexRequest(BaseModel):
    folder: str

class RootRequest(BaseModel):
    path: str

@app.get("/health")
def health_check():
    
    return{
        "Status": "healthy",
        "version":"3.0.0",
    }
    
@app.get("/search")
def search_endpoint(
    q: str = Query(
        min_length=1,
        description="Text to search for",
    ),
    type: str | None = Query(
        default=None,
        description="Optional file extension, e.g. .dart",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results",
    ),
         ):
    
    
    try:
        results = search_files(
            q.strip(),
            limit,
            type,
        )
        
        return {
            "query": q,
            "count": len(results),
            "results": [dict(row) for row in results],
        }
    except sqlite3.OperationalError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
        
        
@app.post("/index")
def index_endpoint(request:IndexRequest):
    
    try:
        folder = Path(request.folder).expanduser().resolve()
        
        index_folder(str(folder))
    except(OSError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    return{
        "status":"Success",
        "folder":str(folder),
        "message": "Folder indexed successfully"
    }
    

@app.get("/roots")
def list_roots():
   
    
    roots = get_search_roots()
    
    return{
        "count":len(roots),
        "roots":
            [{
            "id": root["id"],
            "path": root["path"]
        } for root in roots]
    }
    

@app.post("/roots")
def register_root(request: RootRequest):
    
    initialize_database()
    
    try:
        root = Path(request.path).expanduser().resolve()
        
        if not root.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Folder does not exist: {root}",
            )
        
        if not root.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Not a folder: {root}",
            )
        
        add_search_root(str(root))
        
    except OSError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    return {
        "status": "Success",
        "path": str(root),
        "message": "Search root register successfully",
    }
    
    