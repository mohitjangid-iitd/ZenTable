import json
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_client_data(client_id: str):
    file_path = f"data/{client_id}.json"
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r") as f:
        return json.load(f)

@app.get("/{client_id}", response_class=HTMLResponse)
async def restaurant_home(request: Request, client_id: str):
    """Restaurant's home/landing page"""
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("home.html", {
        "request": request, 
        "client_id": client_id,
        "data": data
    })

@app.get("/{client_id}/ar-menu", response_class=HTMLResponse)
async def ar_menu(request: Request, client_id: str):
    """AR Menu experience page"""
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("ar_menu.html", {
        "request": request, 
        "client_id": client_id
    })

@app.get("/api/menu/{client_id}")
async def get_menu_api(client_id: str):
    """API endpoint for menu data"""
    data = get_client_data(client_id)
    if data:
        return JSONResponse(content=data)
    raise HTTPException(status_code=404, detail="Data not found")

'''
@app.get("/api/restaurant/{client_id}")
async def get_info_c(clint_id: str):
    data = get_client_data(clint_id)
    if data != None:
        return {"Name": data["restaurant"]["name"],
                "Phone": data["restaurant"]["phone"],
                "Address": data["restaurent"]["address"]}
'''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
