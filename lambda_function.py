import requests
from lxml import html
import datetime

def lambda_handler(event, context):
    session_requests = requests.session()

    login_url = "https://www.strava.com/login"
    result = session_requests.get(login_url)

    tree = html.fromstring(result.text)
    authenticity_token = list(set(tree.xpath("//*[@id='login_form']/input[@name='authenticity_token']/@value")))[0]

    payload = {
        "email": "***", 
        "password": "***", 
        "authenticity_token": authenticity_token
    }

    login_result = session_requests.post(
        'https://www.strava.com/session', 
        data = payload, 
        headers = dict(referer=login_url)
    )

    print(login_result)


    def parse_activity_html(activity_html):
        tree = html.fromstring(activity_html.text)

        last_timestamp = ''
        last_month_name = ''

        for activity in tree.xpath("//div[@class='activity entity-details feed-entry']"):
            activity_timestamp = activity.xpath("./@data-rank")[0]
            activity_athlete = activity.xpath(".//a[@class='entry-athlete']")[0].text.strip()
            activity_date = activity.xpath(".//div[@class='entry-head']/time")[0].text.strip()
            activity_date_day, activity_date_time, *_ = activity_date.split(" at ")
            activity_distance = activity.xpath(".//li[@title='Distance']")[0].text.strip()
            try:
                activity_elevation_gain = activity.xpath(".//li[@title='Elev Gain']")[0].text.strip().replace(",", "")
            except IndexError:
                activity_elevation_gain = ""
            print(f'"{activity_athlete}","{activity_date_day}","{activity_date_time}","{activity_distance}","{activity_elevation_gain}"')
            last_timestamp = activity_timestamp
            last_month_name = activity_date_day.split(" ")[0]
        
        return last_timestamp, last_month_name

    club_id = "***"
    current_month = datetime.datetime.now().strftime("%B")

    club_recent_activity = session_requests.get(f'https://www.strava.com/clubs/{club_id}/recent_activity')
    last_timestamp, last_month_name = parse_activity_html(club_recent_activity)

    while last_month_name == current_month:
        club_recent_activity_continued = session_requests.get(f"https://www.strava.com/clubs/{club_id}/feed",
            params = dict(feed_type="club", before=last_timestamp, cursor=last_timestamp + ".0")
        )
        last_timestamp, last_month_name = parse_activity_html(club_recent_activity_continued)

    session_requests.close()
