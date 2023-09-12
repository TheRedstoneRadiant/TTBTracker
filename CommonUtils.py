import json
import nextcord
import phonenumbers
import os

def build_embed_from_json(json_path) -> nextcord.Embed:
    """
    Create a NextCord Embed object from a JSON file
    """
    if type(json_path) == str:
        # Load the embed data from the JSON file
        with open(json_path, "r") as file:
            embed_data = json.load(file)
    else:
        embed_data = json_path

    # Create the embed using the loaded data
    embed = nextcord.Embed(
        title=embed_data["title"],
        description=embed_data["description"],
        color=embed_data["color"]
    )

    for field_data in embed_data["fields"]:
        embed.add_field(
            name=field_data["name"],
            value=field_data["value"],
            inline=field_data["inline"]
        )
    if "footer" in embed_data:
        embed.set_footer(text=embed_data['footer'])

    return embed

def validate_phone_number(phone_number: str) -> bool:
    """
    Method which validates a phone number using the phonenumbers library
    """
    number = phonenumbers.parse(phone_number, "CA")
    return phonenumbers.is_valid_number_for_region(number, "CA")

def sanitize_phone_number(phone_number: str) -> str:
    """
    Method which sanitizes a phone number using the phonenumbers library
    """
    number = phonenumbers.parse(phone_number, "CA")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)

def get_most_recent_file_modified_time(path="."):
    # Initialize variables to store the most recent time and file path
    most_recent_time = 0

    # Walk through all directories and files in the given path
    for root, _, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            # Get the modification time of the current file
            file_mtime = os.path.getmtime(file_path)
            
            # Compare with the current most recent time
            if file_mtime > most_recent_time:
                most_recent_time = file_mtime

    # Return the most recent file's path and modified time
    return most_recent_time