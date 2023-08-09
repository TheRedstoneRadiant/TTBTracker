from pymongo import MongoClient
from typing import List, Optional
import dotenv
dotenv.load_dotenv("tokens.env")

import os

class Mongo:
    """
    Class with abstraction of MongoDB database.
    Allows for easier access to the database.
    """
    
    def __init__(self, db_url: str, db_name: str):
        self.client = MongoClient(db_url)
        self.db = self.client[db_name]

    def add_user_activity(self, user_id: int, course_code: str, semester: str, activity: str):
        """
        Add an activity for a specific user.
        
        Precondition: user_id exists in the database.
        """
        collection = self.db["users"]
        query = {"_id": user_id}
        update = {"$push": {"activity": {"courseCode": course_code, "Semester": semester, "Activity": activity}}}
        collection.update_one(query, update, upsert=True)

    def add_user_new(self, user_id: int, course_code: str, semester: str, activity: str):
        """
        Adds a new section open notification for a specific activity for a user.
        """
        collection = self.db["users"]
        query = {"_id": user_id}
        update = {"$push": {"new": {"courseCode": course_code, "Semester": semester, "Activity": activity}}}
        collection.update_one(query, update, upsert=True)

    def remove_user_activity(self, user_id: int, course_code: str, semester: str, activity: str):
        """
        Remove a specific activity for a user.

        Precondition: user_id exists in the database, and the activity exists for the user.
        """
        collection = self.db["users"]
        query = {"_id": user_id}
        update = {"$pull": {"activity": {"courseCode": course_code, "Semester": semester, "Activity": activity}}}
        collection.update_one(query, update)

    def remove_user_new(self, user_id: int, course_code: str, semester: str, activity: str):
        """
        Removes the new section notification for a specific activity for a user.
        """
        collection = self.db["users"]
        query = {"_id": user_id}
        update = {"$pull": {"new": {"courseCode": course_code, "Semester": semester, "Activity": activity}}}
        collection.update_one(query, update)

    def add_user(self, user_id: int, profile: dict[str, str], campus: str = "UofT"):
        """
        Add a new user to the database.

        Precondition: user_id does not exist in the database.
        """
        collection = self.db["users"]
        collection.insert_one({"_id": user_id, "activity": [], "new": [], "profile": profile, "campus": campus})

    def update_user_profile(self, user_id: int, profile: dict[str, str]):
        """
        Updates a user's profile.
        """
        current_profile = self.get_user_profile(user_id)
        for key, value in profile.items():
            current_profile[key] = value
        collection = self.db["users"]
        collection.update_one({"_id": user_id}, {"$set": {"profile": current_profile}})

    def get_user_profile(self, user_id: int) -> Optional[dict[str, str]]:
        """
        Returns a user's profile.
        Preconditions: user_id exists in the database.
        """
        return self.db["users"].find_one({"_id": user_id}).get("profile", None)

    def remove_user(self, user_id: int):
        """
        Remove a user and all their activities from the database.

        Preconditions: user_id exists in the database.
        """
        collection = self.db["users"]
        collection.delete_one({"_id": user_id})

    def get_user_activities(self, user_id: int) -> List[dict]:
        """
        Get the activities for a specific user.

        Preconditions: user_id exists in the database.
        """
        collection = self.db["users"]
        user_data = collection.find_one({"_id": user_id})
        return user_data.get("activity", [])

    def get_user_news(self, user_id: int) -> List[dict]:
        """
        Returns all new section notifications for a user.
        
        Preconditions: user_id exists in the database.
        """
        collection = self.db["users"]
        user_data = collection.find_one({"_id": user_id})
        return user_data.get("new", [])

    def get_all_users(self, module="UofT") -> List[int]:
        """
        Get a list of all user IDs in the database that have a specific module.
        """
        collection = self.db["users"]
        return [user["_id"] for user in collection.find({"campus": module})]


    def is_user_tracking_activity(self, user_id: int, course_code: str, semester: str, activity: str) -> bool:
        """
        Check if a user is tracking a specific activity.
        Precondition: user_id exists in the database.
        """
        collection = self.db["users"]
        query = {"_id": user_id, "activity": {"$elemMatch": {"courseCode": course_code, "Semester": semester, "Activity": activity}}}
        return bool(collection.count_documents(query) > 0)
    
    def is_user_tracking_new(self, user_id: int, course_code: str, semester: str, activity: str) -> bool:
        """
        Check if a user already has a new section notification for a specific activity.
        """
        collection = self.db["users"]
        query = {"_id": user_id, "new": {"$elemMatch": {"courseCode": course_code, "Semester": semester, "Activity": activity}}}
        return bool(collection.count_documents(query) > 0)
    
    def is_user_in_db(self, user_id: int) -> bool:
        """
        Check if a user with the given user ID exists in the database.
        """
        collection = self.db["users"]
        return bool(collection.count_documents({"_id": user_id}) > 0)

    def get_campus(self, user_id: int) -> str:
        """
        Get the campus of a user.
        Precondition: user_id exists in the database.
        """
        collection = self.db["users"]
        return collection.find_one({"_id": user_id}).get("campus", None)

    def add_course_sections(self, course_code: str, semester: str, activity_type: str, sections: list[str]):
        """
        Add a list of sections for a course to the database.
        This should insert it into this format:
        _id: semester: {
            courseCode: {
                activity_type: { 
                [sections]
                }
            }
        }
        This method should work regardless of whether the course already exists in the database or not
        """
        collection = self.db["courses"]
        update_query = {
            f"{course_code}.{activity_type}": {"$each": sections}
        }

        # Update the document in the database
        collection.update_one(
            {"_id": semester},
            {"$addToSet": update_query},
            upsert=True
        )
        

if __name__ == "__main__":
    db_url = os.getenv("PYMONGO")  # Replace with your MongoDB URL
    db_name = "TTBTrackrDev"  # Replace with your database name

    # Initialize the abstraction layer
    db = Mongo(db_url, db_name)
    
    db.add_course_sections("CSC148", "F", "LEC", ["L0101", "L0201"])
    db.add_course_sections("CSC148", "F", "PRA", ["PRA0101", "PRA0102"])

