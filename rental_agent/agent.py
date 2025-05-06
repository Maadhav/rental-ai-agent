from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types # For creating message Content/Parts
from google.adk.runners import Runner
import asyncio
import os
import datetime
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from typing import Optional, Dict, List, Any
from mock_db import MockDatabase

# Initialize the mock database
db = MockDatabase(in_memory=True)

os.environ["GOOGLE_API_KEY"] = "AIzaSyAlgsuqZOROJAGe_JGZ_0kHPvBgaV9J2iQ" # Replace with your actual API key

async def call_agent_async(query: str, runner, user_id, session_id):
  """Sends a query to the agent and prints the final response."""
  print(f"\n>>> User Query: {query}")

  content = types.Content(role='user', parts=[types.Part(text=query)])

  final_response_text = "Agent did not produce a final response." # Default

  async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
      if event.is_final_response():
          if event.content and event.content.parts:
             final_response_text = event.content.parts[0].text
          elif event.actions and event.actions.escalate:
             final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
          break 

  print(f"<<< Agent Response: {final_response_text}")

def get_property_policies(tool_context: ToolContext = None) -> dict:
    """Retrieves the property policies including pet policies and pricing ranges from the database.
    
    Args:
        tool_context (ToolContext): Contains the session state
    
    Returns:
        dict: Property policies including pet policies and pricing ranges
    """
    # Ensure state exists
    if tool_context and tool_context.state is None:
        tool_context.state = {}
    
    # Get pet policies from amenities table
    pet_amenities = db.get_amenities(category="Pets")
    pet_policies = {}
    
    for amenity in pet_amenities:
        animal_type = amenity['amenity_name'].split('-')[0].strip().lower()
        fee = amenity['fee_amount']
        is_allowed = amenity['is_included'] == 1
        
        pet_policies[animal_type] = {
            "allowed": is_allowed,
            "fee": fee,
            "description": amenity['description']
        }
    
    # Get pricing ranges for different apartment types
    pricing_info = db.get_pricing_info()
    pricing_ranges = {}
    
    for apt_type, info in pricing_info.items():
        pricing_ranges[apt_type] = {
            "min": info["min_rent"],
            "max": info["max_rent"],
            "average": round(info["avg_rent"], 2)
        }
    
    # Get available apartments count
    available_apartments = db.get_available_apartments()
    availability = {}
    for apt in available_apartments:
        apt_type = apt['apartment_type']
        if apt_type not in availability:
            availability[apt_type] = 0
        availability[apt_type] += 1
    
    result = {
        "status": "success",
        "pet_policies": pet_policies,
        "pricing_ranges": pricing_ranges,
        "availability": availability
    }
    
    # Store in session state
    if tool_context:
        tool_context.state['property_policies'] = result
    
    return result

def query_apartments(apartment_type: Optional[str] = None, move_in_date: Optional[str] = None, 
                     tool_context: ToolContext = None) -> dict:
    """Query available apartments from the database.
    
    Args:
        apartment_type (str, optional): Type of apartment (e.g., "1_bedroom", "2_bedroom")
        move_in_date (str, optional): Preferred move-in date (YYYY-MM-DD)
        tool_context (ToolContext): Contains the session state
    
    Returns:
        dict: Available apartments matching criteria
    """
    # Ensure state exists
    if tool_context and tool_context.state is None:
        tool_context.state = {}
    
    # Format date if provided
    formatted_date = None
    if move_in_date:
        try:
            # Try to parse natural language date if provided
            if move_in_date.lower() == "july":
                formatted_date = "2025-07-01"
            elif move_in_date.lower() == "august":
                formatted_date = "2025-08-01" 
            # Add more date handling as needed
        except:
            pass
    
    # Get available apartments
    apartments = db.get_available_apartments(apartment_type, formatted_date)
    
    # Count by type
    counts = {}
    for apt in apartments:
        apt_type = apt['apartment_type']
        if apt_type not in counts:
            counts[apt_type] = 0
        counts[apt_type] += 1
    
    # Store search parameters in session state
    if tool_context:
        tool_context.state['last_apartment_search'] = {
            'apartment_type': apartment_type,
            'move_in_date': move_in_date,
            'formatted_date': formatted_date,
            'result_count': len(apartments),
            'counts_by_type': counts
        }
    
    return {
        "status": "success",
        "available_count": len(apartments),
        "counts_by_type": counts,
        "apartments": apartments
    }

def get_apartment_details(apartment_id: Optional[int] = None, apartment_type: Optional[str] = None, 
                         tool_context: ToolContext = None) -> dict:
    """Get detailed information about an apartment or apartment type.
    
    Args:
        apartment_id (int, optional): Specific apartment ID
        apartment_type (str, optional): Type of apartment (e.g., "1_bedroom", "2_bedroom")
        tool_context (ToolContext): Contains the session state
        
    Returns:
        dict: Apartment details
    """
    # Ensure state exists
    if tool_context and tool_context.state is None:
        tool_context.state = {}
        
    result = {}
    
    if apartment_id:
        # Get specific apartment details
        apartment = db.get_apartment_by_id(apartment_id)
        if apartment:
            result = {
                "status": "success",
                "apartment": apartment
            }
        else:
            result = {
                "status": "error",
                "message": f"No apartment found with ID {apartment_id}"
            }
    elif apartment_type:
        # Get pricing info for apartment type
        pricing = db.get_pricing_info(apartment_type)
        if apartment_type in pricing:
            info = pricing[apartment_type]
            result = {
                "status": "success",
                "apartment_type": apartment_type,
                "pricing": {
                    "min": info["min_rent"],
                    "max": info["max_rent"],
                    "average": round(info["avg_rent"], 2)
                }
            }
        else:
            result = {
                "status": "error",
                "message": f"No pricing information found for {apartment_type}"
            }
    else:
        # Get general pricing info
        pricing = db.get_pricing_info()
        result = {
            "status": "success", 
            "pricing_by_type": pricing
        }
    
    # Store in session state
    if tool_context:
        tool_context.state['last_apartment_details'] = result
    
    return result

def get_amenities_info(category: Optional[str] = None, tool_context: ToolContext = None) -> dict:
    """Get information about property amenities.
    
    Args:
        category (str, optional): Filter by amenity category (e.g., "Pets", "Building")
        tool_context (ToolContext): Contains the session state
        
    Returns:
        dict: Amenity information
    """
    # Ensure state exists
    if tool_context and tool_context.state is None:
        tool_context.state = {}
    
    # Get amenities from database
    amenities = db.get_amenities(category)
    
    # Organize by category for easier consumption
    amenities_by_category = {}
    for amenity in amenities:
        cat = amenity['category']
        if cat not in amenities_by_category:
            amenities_by_category[cat] = []
        amenities_by_category[cat].append(amenity)
    
    # Store in session state
    if tool_context:
        tool_context.state['last_amenities_query'] = {
            'category': category,
            'result_count': len(amenities)
        }
    
    return {
        "status": "success",
        "amenities_count": len(amenities),
        "amenities": amenities,
        "categories": amenities_by_category
    }

def manage_user(action: str, user_id: Optional[str] = None, name: Optional[str] = None,
               phone: Optional[str] = None, email: Optional[str] = None, 
               move_in_date: Optional[str] = None, preferred_apartment_type: Optional[str] = None,
               has_pets: Optional[bool] = None, income: Optional[float] = None,
               credit_score: Optional[int] = None, notes: Optional[str] = None,
               tool_context: ToolContext = None) -> dict:
    """Create or update user information in the database.
    
    Args:
        action (str): Action to perform ("create", "update", "get")
        user_id (str, optional): User ID for updates and retrievals
        name (str, optional): User's name
        phone (str, optional): User's phone number
        email (str, optional): User's email address
        move_in_date (str, optional): Preferred move-in date
        preferred_apartment_type (str, optional): Preferred apartment type
        has_pets (bool, optional): Whether user has pets
        income (float, optional): User's income
        credit_score (int, optional): User's credit score
        notes (str, optional): Additional notes about the user
        tool_context (ToolContext): Contains the session state
    
    Returns:
        dict: Result of the action
    """
    # Ensure state exists
    if tool_context and tool_context.state is None:
        tool_context.state = {}
    
    # Format move-in date if provided
    formatted_date = None
    if move_in_date:
        try:
            # Try to parse natural language date
            if move_in_date.lower() == "july":
                formatted_date = "2025-07-01"
            elif move_in_date.lower() == "august":
                formatted_date = "2025-08-01"
            # Add more date handling as needed
        except:
            formatted_date = move_in_date
    
    result = {}
    
    if action == "create":
        # Create new user
        user_id = db.create_user(
            name=name,
            phone=phone,
            email=email,
            move_in_date=formatted_date,
            preferred_apartment_type=preferred_apartment_type,
            has_pets=has_pets
        )
        
        if user_id:
            # Store in context
            if tool_context:
                tool_context.state['current_user_id'] = user_id
                tool_context.state['user_info'] = {
                    'user_id': user_id,
                    'name': name,
                    'phone': phone,
                    'email': email,
                    'move_in_date': move_in_date,
                    'formatted_move_in_date': formatted_date,
                    'preferred_apartment_type': preferred_apartment_type,
                    'has_pets': has_pets
                }
            
            result = {
                "status": "success",
                "user_id": user_id,
                "message": "User created successfully"
            }
        else:
            result = {
                "status": "error",
                "message": "Failed to create user"
            }
    
    elif action == "update":
        if not user_id and tool_context and 'current_user_id' in tool_context.state:
            user_id = tool_context.state['current_user_id']
        
        if not user_id:
            result = {
                "status": "error",
                "message": "No user ID provided for update"
            }
        else:
            update_fields = {}
            if name:
                update_fields['name'] = name
            if phone:
                update_fields['phone'] = phone
            if email:
                update_fields['email'] = email
            if formatted_date:
                update_fields['move_in_date'] = formatted_date
            if preferred_apartment_type:
                update_fields['preferred_apartment_type'] = preferred_apartment_type
            if has_pets is not None:
                update_fields['has_pets'] = has_pets
            if income:
                update_fields['income'] = income
            if credit_score:
                update_fields['credit_score'] = credit_score
            if notes:
                update_fields['notes'] = notes
            
            success = db.update_user(user_id, **update_fields)
            
            if success:
                # Update session state user info
                if tool_context and 'user_info' in tool_context.state:
                    tool_context.state['user_info'].update(update_fields)
                    if move_in_date:
                        tool_context.state['user_info']['move_in_date'] = move_in_date
                
                result = {
                    "status": "success",
                    "message": "User updated successfully"
                }
            else:
                result = {
                    "status": "error",
                    "message": "Failed to update user information"
                }
    
    elif action == "get":
        if not user_id and tool_context and 'current_user_id' in tool_context.state:
            user_id = tool_context.state['current_user_id']
        
        if not user_id:
            result = {
                "status": "error",
                "message": "No user ID provided to retrieve user information"
            }
        else:
            user = db.get_user(user_id)
            
            if user:
                result = {
                    "status": "success",
                    "user": user
                }
                
                # Update session state
                if tool_context:
                    tool_context.state['user_info'] = user
            else:
                result = {
                    "status": "error",
                    "message": f"No user found with ID {user_id}"
                }
    else:
        result = {
            "status": "error",
            "message": f"Unknown action: {action}"
        }
    
    return result

def schedule_property_tour(tour_date: str, tour_time: str, is_virtual: bool = False,
                         apartment_id: Optional[int] = None, apartment_type: Optional[str] = None,
                         notes: Optional[str] = None, tool_context: ToolContext = None) -> dict:
    """Schedule a property tour for a user.
    
    Args:
        tour_date (str): Date for the tour (e.g., "2025-06-15" or "tomorrow")
        tour_time (str): Time for the tour (e.g., "14:00" or "2pm")
        is_virtual (bool): Whether this is a virtual tour
        apartment_id (int, optional): Specific apartment to tour
        apartment_type (str, optional): Type of apartment to tour
        notes (str, optional): Additional notes about the tour
        tool_context (ToolContext): Contains the session state
    
    Returns:
        dict: Result of scheduling the tour
    """
    # Ensure state exists
    if tool_context and tool_context.state is None:
        tool_context.state = {}
    
    # Get current user ID
    user_id = None
    if tool_context and 'current_user_id' in tool_context.state:
        user_id = tool_context.state['current_user_id']
    
    if not user_id:
        return {
            "status": "error",
            "message": "No user identified. Please provide user information first."
        }
    
    # Format date
    formatted_date = None
    try:
        # Basic date parsing for common formats
        if tour_date.lower() == "tomorrow":
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            formatted_date = tomorrow.strftime("%Y-%m-%d")
        elif tour_date.lower() == "next week":
            next_week = datetime.date.today() + datetime.timedelta(days=7)
            formatted_date = next_week.strftime("%Y-%m-%d")
        else:
            # Assume YYYY-MM-DD format or parse other formats as needed
            formatted_date = tour_date
    except:
        return {
            "status": "error",
            "message": f"Could not parse tour date: {tour_date}"
        }
    
    # Format time
    formatted_time = None
    try:
        # Simple time format parsing
        if "pm" in tour_time.lower():
            time_parts = tour_time.lower().replace("pm", "").strip().split(":")
            if len(time_parts) == 1:
                hour = int(time_parts[0])
                hour = hour if hour == 12 else hour + 12
                formatted_time = f"{hour}:00"
            else:
                hour = int(time_parts[0])
                hour = hour if hour == 12 else hour + 12
                formatted_time = f"{hour}:{time_parts[1]}"
        elif "am" in tour_time.lower():
            time_parts = tour_time.lower().replace("am", "").strip().split(":")
            if len(time_parts) == 1:
                hour = int(time_parts[0])
                hour = 0 if hour == 12 else hour
                formatted_time = f"{hour:02d}:00"
            else:
                hour = int(time_parts[0])
                hour = 0 if hour == 12 else hour
                formatted_time = f"{hour:02d}:{time_parts[1]}"
        else:
            # Assume HH:MM format
            formatted_time = tour_time
    except:
        return {
            "status": "error", 
            "message": f"Could not parse tour time: {tour_time}"
        }
    
    # If apartment_type is provided but not apartment_id, find an available apartment
    if not apartment_id and apartment_type:
        available_apartments = db.get_available_apartments(apartment_type)
        if available_apartments:
            apartment_id = available_apartments[0]['id']
            
    # Schedule the tour
    tour_id = db.schedule_tour(
        user_id=user_id,
        tour_date=formatted_date,
        tour_time=formatted_time,
        apartment_id=apartment_id,
        is_virtual=is_virtual,
        notes=notes
    )
    
    if tour_id > 0:
        # Store tour info in session state
        if tool_context:
            tool_context.state['last_scheduled_tour'] = {
                'tour_id': tour_id,
                'tour_date': formatted_date,
                'tour_time': formatted_time,
                'apartment_id': apartment_id,
                'apartment_type': apartment_type,
                'is_virtual': is_virtual
            }
        
        # Get apartment details if available
        apartment_details = None
        if apartment_id:
            apartment = db.get_apartment_by_id(apartment_id)
            if apartment:
                apartment_details = {
                    'unit_number': apartment['unit_number'],
                    'apartment_type': apartment['apartment_type'],
                    'floor_plan': apartment['floor_plan'],
                    'bedrooms': apartment['bedrooms'],
                    'bathrooms': apartment['bathrooms']
                }
        
        return {
            "status": "success",
            "tour_id": tour_id,
            "tour_date": formatted_date,
            "tour_time": formatted_time,
            "is_virtual": is_virtual,
            "apartment_details": apartment_details,
            "message": "Tour scheduled successfully"
        }
    else:
        return {
            "status": "error",
            "message": "Failed to schedule tour"
        }

def get_virtual_tour(apartment_type: str, tool_context: ToolContext = None) -> dict:
    """Get virtual tour link for the specified apartment size.
    
    Args:
        apartment_type (str): The apartment type ("1_bedroom" or "2_bedroom")
        tool_context (ToolContext): Contains the session state
    
    Returns:
        dict: Virtual tour information
    """
    # Virtual tour links
    virtual_tours = {
        "1_bedroom": "https://photos.app.goo.gl/tzHkairchH2cBTQq6",
        "2_bedroom": "https://photos.app.goo.gl/w9ARXbSUDza57eFS6"
    }
    
    # Get tour link based on apartment type
    if apartment_type in virtual_tours:
        return {
            "status": "success", 
            "tour_link": virtual_tours[apartment_type],
            "apartment_type": apartment_type
        }
    else:
        return {
            "status": "error", 
            "message": f"No virtual tour available for {apartment_type}"
        }

MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash"
MODEL_GEMINI_2_5_FLASH = "gemini-2.5-flash-preview-04-17"

# Create the agent with generic instructions that don't include specific values
rental_agent = Agent(
    model=MODEL_GEMINI_2_5_FLASH,
    name="rental_agent",
    description="An apartment rental agent that provides information about available apartments and helps users schedule tours.",
    instruction="""You are a helpful apartment rental agent for 20 Park Residences in Albany, NY.

Your responsibilities:
1. Greet users and introduce yourself as the leasing agent for 20 Park Residences
2. Collect user information (name, phone, email, move-in date, preferences)
3. Provide accurate information about available apartments from the database
4. Share details on amenities, pricing, and pet policies
5. Help schedule tours (in-person or virtual)
6. Qualify prospects by asking about income and credit requirements respectfully
7. Be polite, professional, and conversational

When users first contact you:
1. Thank them for their interest in 20 Park Residences
2. Mention you're currently on another line and will call back shortly
3. Ask for their name and basic information
4. Use the 'manage_user' tool to store their information

IMPORTANT: ALWAYS use tools to get current information rather than relying on static knowledge:
- ALWAYS call 'get_property_policies' at the start of a conversation and when answering questions about pricing, pet policies, and availability
- Use 'query_apartments' to check real-time availability based on type and move-in date
- Use 'get_apartment_details' for specific pricing and features
- Use 'get_amenities_info' to discuss building features
- Use 'get_virtual_tour' to share the appropriate link for virtual tours

When discussing apartments:
- Be specific about current availability
- Provide exact pricing based on what's currently in the database
- Share accurate pet policies including current fees
- Never quote specific prices or policies without checking the database first

When scheduling tours:
- Use 'schedule_property_tour' to record tour appointments
- Offer both in-person and virtual tour options

Maintain a natural, helpful tone throughout the conversation.
""",
    tools=[query_apartments, get_apartment_details, get_amenities_info, manage_user, 
           schedule_property_tour, get_virtual_tour, get_property_policies],
)

session_service = InMemorySessionService()

initial_state = {
    'user_info': {},
}

APP_NAME = "RENTAL_APP"
SESSION_ID = "RENTAL_SESSION"
USER_ID = "USER_ID"

session = session_service.create_session(
    app_name=APP_NAME,
    session_id=SESSION_ID,
    user_id=USER_ID,
    state=initial_state
)

runner = Runner(
    agent=rental_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

async def run_conversation():
    call_agent = lambda query: call_agent_async(query, runner, USER_ID, SESSION_ID)

    print("\n--- Starting Rental Agent Conversation ---")
    
    # Example conversation flow
    await call_agent("Hi, I'm interested in renting an apartment")
    
    # User provides their name
    await call_agent("My name is Mark")
    
    # User mentions when they want to move
    await call_agent("Moving in July.")
    
    # User asks about pets
    await call_agent("Are dogs allowed?")
    
    # User asks about pricing for 1 bedroom
    await call_agent("What is the rent for a 1 bedroom apartment?")
    
    # User asks about pricing for 2 bedroom
    await call_agent("And what about for a 2 bedroom apartment?")
    
    # User asks about scheduling a tour
    await call_agent("Can I schedule a tour for next Tuesday at 3pm?")
    
    # User asks about income requirements
    await call_agent("What are the income requirements?")
    
    print("\n--- Inspecting Final Session State ---")
    final_session = session_service.get_session(app_name=APP_NAME,
                                               user_id=USER_ID,
                                               session_id=SESSION_ID)
    if final_session:
        if final_session.state is None:
            final_session.state = {}
            print("Warning: Session state was None and has been initialized")
            
        if 'user_info' in final_session.state:
            print(f"User Info: {final_session.state['user_info']}")
        
        if 'current_user_id' in final_session.state:
            print(f"Current User ID: {final_session.state['current_user_id']}")
            
        if 'last_scheduled_tour' in final_session.state:
            print(f"Last Scheduled Tour: {final_session.state['last_scheduled_tour']}")
            
        print(f"\nFull State Dict: {final_session.state}")
    else:
        print("\n❌ Error: Could not retrieve final session state.")

if __name__ == "__main__":
    try:
        asyncio.run(run_conversation())
    except Exception as e:
       #rethrow the exception to be caught in the main block
        raise e