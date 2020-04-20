# import requests
from botocore.vendored import requests
from lxml import html
import datetime, os

def parse_activity_html(activity_html):
    '''
    parse the html responce from strava
    '''
    tree = html.fromstring(activity_html.text)

    last_timestamp = ''
    records = []

    for activity in tree.xpath("//div[@class='activity entity-details feed-entry']"):
        activity_timestamp = activity.xpath("./@data-rank")[0]
        activity_athlete = activity.xpath(".//a[@class='entry-athlete']")[0].text.strip()
        activity_date = activity.xpath(".//div[@class='entry-head']/time")[0].text.strip()
        activity_date_day, activity_date_time, *_ = activity_date.split(" at ")
        # correct the dates from human readable to date time
        if activity_date_day == 'Today':
            activity_date_day = datetime.date.today().strftime('%B %-d, %Y')
        elif activity_date_day == 'Yesterday':
            activity_date_day = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%B %-d, %Y')
        activity_distance = activity.xpath(".//li[@title='Distance']")[0].text.strip()
        try:
            activity_elevation_gain = activity.xpath(".//li[@title='Elev Gain']")[0].text.strip().replace(',', '')
        except IndexError:
            activity_elevation_gain = ''
        records.append((activity_athlete, activity_date_day, activity_date_time, activity_distance, activity_elevation_gain))
        last_timestamp = activity_timestamp

    return last_timestamp, records


def lambda_handler(event, context):
    '''
    Lambda handler
    '''
    # get the club id
    club_id = os.environ['CLUB_ID']
    
    # open session
    session_requests = requests.session()

    # get a token for this session
    login_url = 'https://www.strava.com/login'
    result = session_requests.get(login_url)
    tree = html.fromstring(result.text)
    authenticity_token = list(set(tree.xpath("//*[@id='login_form']/input[@name='authenticity_token']/@value")))[0]

    # login
    login_result = session_requests.post(
        'https://www.strava.com/session', 
        data = dict(email=os.environ['EMAIL'], password=os.environ['PASSWORD'], authenticity_token=authenticity_token), 
        headers = dict(referer=login_url)
    )

    # resulting activity records from strava
    records = []
    
    # get the recent activity
    club_recent_activity = session_requests.get(f'https://www.strava.com/clubs/{club_id}/recent_activity')
    last_timestamp, temp_records = parse_activity_html(club_recent_activity)
    records += temp_records

    # load more until we can
    while len(temp_records) > 0:
        club_recent_activity_continued = session_requests.get(f"https://www.strava.com/clubs/{club_id}/feed",
            params = dict(feed_type='club', before=last_timestamp, cursor=last_timestamp + ".0")
        )
        last_timestamp, temp_records = parse_activity_html(club_recent_activity_continued)
        records += temp_records

    # close the session
    session_requests.close()

    return {'content' : records}
