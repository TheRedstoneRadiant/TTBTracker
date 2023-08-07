import json
import nextcord
import phonenumbers

def build_embed_from_json(json_path: str) -> nextcord.Embed:
    # Load the embed data from the JSON file
    with open(json_path, "r") as file:
        embed_data = json.load(file)

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

    return embed

def validate_phone_number(phone_number: str) -> bool:
    """
    Method which validates a phone number using the phonenumbers library
    """
    number = phonenumbers.parse(phone_number, "CA")
    return phonenumbers.is_valid_number_for_region(number, "CA")