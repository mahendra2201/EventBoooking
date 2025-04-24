from fastapi import FastAPI, Request, Form, HTTPException, Depends,Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import os
import uvicorn

app = FastAPI()

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["EventBooking"]
register_collection = db["register"]
login_collection = db["login"]
booking_collection = db["bookings"]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

    
    return templates.TemplateResponse("home.html", {
        "request": request,
        "name": username  # Changed to match your template variable
    })

@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/user_register")
async def user_register(
    request: Request,
    username: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    mobile: str = Form(...),
    password: str = Form(...)
):
    # Check if email or username already exists
    existing_user = register_collection.find_one({"$or": [{"email": email}, {"username": username}]})
    if existing_user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Email or Username already exists"
        })

    # Save new user
    register_collection.insert_one({
        "username": username,
        "name": name,
        "email": email,
        "mobile": mobile,
        "password": password  # ⚠️ Hash in real apps
    })

    return RedirectResponse(url="/login", status_code=302)
    
# Pydantic model for booking data validation
class Booking(BaseModel):
    service_name: str
    date: str
    username: str
    guests: Optional[int] = None
    duration: Optional[int] = None
    employees: Optional[int] = None
    theme: Optional[str] = None
    family_size: Optional[int] = None
    dietary_requirements: Optional[str] = None
    special_requirements: Optional[str] = None
    contact_number: Optional[str] = None
    price_estimate: Optional[str] = None
    status: str = "pending"

# Login route
@app.post("/user_login")
async def user_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    # Validate login credentials
    user = register_collection.find_one({"email": email, "password": password})
    
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password"
        })

    username = user.get("username")

    # Check if the login data already exists
    existing_login = login_collection.find_one({"email": email})
    if not existing_login:
        login_collection.insert_one({
            "email": email,
            "password": password,
            "username": username
        })

    # ✅ Render home.html instead of redirecting
    return templates.TemplateResponse("home.html", {
        "request": request,
        "username": username
    })

# Home route
@app.get("/home")
async def home(request: Request, username: str = None):
    return templates.TemplateResponse(
        "home.html", 
        {
            "request": request,
            "username": username
        }
    )


# Booking route
@app.post("/book-service/{service_id}")

async def book_service(
    request: Request,
    service_id: int,
    date: str = Form(...),
    username: str = Form(...),
    guests: Optional[int] = Form(None),
    duration: Optional[int] = Form(None),
    employees: Optional[int] = Form(None),
    theme: Optional[str] = Form(None),
    family_size: Optional[int] = Form(None),
    dietary_requirements: Optional[str] = Form(None),
    special_requirements: Optional[str] = Form(None),
    contact_number: Optional[str] = Form(None),
):
    # Service details
    service_details = {
        1: {"service_name": "Gourmet Family Dining", "price_estimate": "From $89/person"},
        2: {"service_name": "Executive Board Retreat", "price_estimate": "From $1,200/day"},
        3: {"service_name": "Corporate Celebration Package", "price_estimate": "Custom Pricing"},
        4: {"service_name": "Signature Birthday Experience", "price_estimate": "From $1,500"},
        5: {"service_name": "Generational Gathering Package", "price_estimate": "From $2,000"},
        6: {"service_name": "Platinum Private Event Suite", "price_estimate": "From $5,000"}
    }
    
    if service_id not in service_details:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Validate date
    try:
        booking_date = datetime.strptime(date, "%Y-%m-%d").date()
        if booking_date < datetime.now().date():
            raise HTTPException(status_code=400, detail="Booking date cannot be in the past")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Create booking document

    user = register_collection.find_one({"username":username})
    booking_data = {
        "mobile_number":user.get("mobile"),
        "service_id": service_id,
        "service_name": service_details[service_id]["service_name"],
        "date": date,
        "username": username,
        "booking_timestamp": datetime.now(),
        "status": "pending",
        "price_estimate": service_details[service_id]["price_estimate"]
    }
    
    # Add optional fields
    optional_fields = {
        "guests": guests,
        "duration": duration,
        "employees": employees,
        "theme": theme,
        "family_size": family_size,
        "dietary_requirements": dietary_requirements,
        "special_requirements": special_requirements,
        "contact_number": contact_number
    }
    
    for field, value in optional_fields.items():
        if value is not None:
            booking_data[field] = value
    
    # Insert booking
    result = booking_collection.insert_one(booking_data)
    
    # Redirect to confirmation
    return RedirectResponse(url=f"/booking-confirmation/{result.inserted_id}", status_code=303)
# Booking confirmation route
@app.get("/booking-confirmation/{booking_id}", response_class=HTMLResponse)
async def booking_confirmation(request: Request, booking_id: str):
    user = ""
    try:
        booking = booking_collection.find_one({"_id": ObjectId(booking_id)})
        if booking:
            user = booking.get("username")
    except:
        booking = None
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return templates.TemplateResponse(
        "booking_confirmation.html",
        {
            "request": request,
            "booking": booking,
            "booking_id": booking_id,
            "username": user
        }
    )
# current_bookings

@app.get("/current-bookings", response_class=HTMLResponse)
async def get_current_bookings(
    request: Request,
    username: str = Query(None, description="Filter bookings by username")
):
    # Get today's date at midnight (00:00)
    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Get tomorrow's date at midnight (00:00)
    tomorrow_midnight = today_midnight + timedelta(days=1)
    
    # Base query for today's bookings
    query = {
        "booking_timestamp": {
            "$gte": today_midnight,
            "$lt": tomorrow_midnight
        }
    }
    
    # Add username filter if provided
    if username:
        query["username"] = username
    
    # Query bookings
    current_bookings = list(booking_collection.find(query))
    
    # Convert ObjectId to string for each booking
    for booking in current_bookings:
        booking["_id"] = str(booking["_id"])
    
    return templates.TemplateResponse(
        "Bookings.html",
        {
            "request": request,
            "bookings": current_bookings,
            "current_date": today_midnight.strftime("%Y-%m-%d"),
            "filtered_username": username  # Pass the username to the template
        }
    )

#current Bookings

@app.get("/current-bookings", response_class=HTMLResponse)
async def get_current_bookings(
    request: Request,
    username: str = Query(None, description="Filter bookings by username")
):
    # Get today's date at midnight (00:00)
    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Base query for current and future bookings
    query = {
        "date": {  # Assuming you have a 'date' field in your bookings
            "$gte": today_midnight.strftime("%Y-%m-%d")  # Format as string if your dates are stored as strings
        }
    }
    
    # Alternative if your dates are stored as datetime objects:
    # query = {
    #     "date": {
    #         "$gte": today_midnight
    #     }
    # }
    
    # Add username filter if provided
    if username:
        query["username"] = username
    
    # Query bookings and sort by date ascending
    current_bookings = list(booking_collection.find(query).sort("date", 1))
    
    # Convert ObjectId to string for each booking
    for booking in current_bookings:
        booking["_id"] = str(booking["_id"])
    
    return templates.TemplateResponse(
        "Bookings.html",
        {
            "request": request,
            "bookings": current_bookings,
            "current_date": today_midnight.strftime("%Y-%m-%d"),
            "filtered_username": username
        }
    )
# previos Bookings


@app.get("/previous-bookings", response_class=HTMLResponse)
async def get_previous_bookings(
    request: Request,
    username: str = Query(..., description="Filter bookings by username")  # Requires username
):
    # Get today's date at midnight (00:00)
    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Query bookings before today for the specific user
    previous_bookings = list(booking_collection.find({
        "username": username,  # Filter by username
        "booking_timestamp": {
            "$lt": today_midnight  # Only bookings before today
        }
    }).sort("booking_timestamp", -1))  # Sort by most recent first
    
    # Convert ObjectId to string for each booking
    for booking in previous_bookings:
        booking["_id"] = str(booking["_id"])
    
    return templates.TemplateResponse(
        "previous_bookings.html",
        {
            "request": request,
            "bookings": previous_bookings,
            "username": username,
            "current_date": today_midnight.strftime("%Y-%m-%d")
        }
    )
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
