import json
import requests
from intervaltree import Interval, IntervalTree

from TTBAPI import TTBAPI
from time import sleep
api = TTBAPI()

x = api._make_request("", "")

headers = {
    'authority': 'api.viaplanner.ca',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'dnt': '1',
    'origin': 'https://timetable.viaplanner.ca',
    'prefer': 'safe',
    'referer': 'https://timetable.viaplanner.ca/',
    'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Microsoft Edge";v="116"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76',
}


template = {
    "F": {
        "MONDAY": {},
        "TUESDAY": {},
        "WEDNESDAY": {},
        "THURSDAY": {},
        "FRIDAY": {},
        "SATURDAY": {},
    },
    "S": {
        "MONDAY": {},
        "TUESDAY": {},
        "WEDNESDAY": {},
        "THURSDAY": {},
        "FRIDAY": {},
        "SATURDAY": {},
    }
}


room_availibility_tree = IntervalTree()
total_api_requests = 0
for course1 in x['payload']['pageableCourse']['courses']:
    course = requests.get(
        f'https://api.viaplanner.ca/courses/{course1["code"]}{course1["sectionCode"]}', headers=headers)
    total_api_requests += 1
    if total_api_requests % 20 == 0:
        sleep(60)
    sleep(0.5)
    text = course.text
    course = course.json()
    try:
        for meeting_section in course['meeting_sections']:
            for time in meeting_section['times']:
                room = time['location']
                start = time["start"]
                end = time['end']
                day = time['day']
                print(
                    f"{course['courseCode']} runs on {day} from {start} to {end} in {room}")
                if course['courseCode'] != "S":
                    if room in template["F"][day]:
                        template["F"][day][room].append((start, end))
                    else:
                        template["F"][day][room] = [(start, end)]
                if course['courseCode'] != "F":
                    if room in template["S"][day]:
                        template["S"][day][room].append((start, end))
                    else:
                        template["S"][day][room] = [(start, end)]
    except Exception as e:
        print(e)
        pass

with open("rooms.json", "w") as file:
    json.dump(template, file)

x = 1
