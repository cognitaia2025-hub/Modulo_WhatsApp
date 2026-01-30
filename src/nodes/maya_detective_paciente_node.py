from pydantic import BaseModel
from typing import Union, Optional

class UserQuery(BaseModel):
    intent: str
    day: Optional[str] = None
    time: Optional[str] = None
    greeting: Optional[str] = None
    location: Optional[str] = None
    hours: Optional[str] = None

class MayaDetectivePacienteNode:

    def handle_query(self, query: UserQuery) -> str:
        if query.greeting:
            return "Hello! How can I assist you today?"
        
        if query.location:
            return "We are located in XYZ."
        
        if query.hours:
            return "Our business hours are from 9 AM to 5 PM."

        if query.intent == "booking":
            return f"Booking for {query.day} at {query.time} has been detected."
        
        if query.intent == "cancellation":
            return "Processing cancellation request."
        
        if query.intent == "rescheduling":
            return "Processing rescheduling request."

        return "I'm not sure how to assist with that."