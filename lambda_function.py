# import requests
from botocore.vendored import requests
from lxml import html
import datetime, os

def human_readable_time_to_machine(activity_date_day):
    '''
    correct the dates from human readable to date time
    '''
    if activity_date_day == 'Today':
        return datetime.date.today().strftime('%B %-d, %Y')
    if activity_date_day == 'Yesterday':
        return (datetime.date.today() - datetime.timedelta(days=1)).strftime('%B %-d, %Y')

def parse_athlete_activity_info(athlete_info):
    '''
    get activity info from athlete selection
    '''
    activity_athlete = athlete_info.xpath(".//a[contains(@class, 'entry-athlete')]")[0].text.strip()
    activity_distance = athlete_info.xpath(".//li[@title='Distance']")[0].text.strip()
    try:
        activity_elevation_gain = athlete_info.xpath(".//li[@title='Elev Gain']")[0].text.strip().replace(',', '')
    except IndexError:
        activity_elevation_gain = ''
    return activity_athlete, activity_distance, activity_elevation_gain


def parse_activity_html(activity_html):
    '''
    parse the html responce from strava
    '''
    tree = html.fromstring(activity_html.text)

    last_timestamp = ''
    records = set()

    # single activities
    for activity in tree.xpath("//div[@class='activity entity-details feed-entry']"):
        # activitiy time stamp
        activity_timestamp = activity.xpath("./@data-rank")[0]
        # activitiy date
        activity_date = activity.xpath(".//div[@class='entry-head']/time")[0].text.strip()
        activity_date_day, activity_date_time, *_ = activity_date.split(" at ")
        activity_date = human_readable_time_to_machine(activity_date_day)
        # athlete info
        activity_athlete, activity_distance, activity_elevation_gain = parse_athlete_activity_info(activity)
        records.add((activity_athlete, activity_date_day, activity_date_time, activity_distance, activity_elevation_gain))
        last_timestamp = activity_timestamp
    
    # group activities
    for activity in tree.xpath("//div[@class='feed-entry group-activity']"):
        # activitiy time stamp
        activity_timestamp = activity.xpath("./@data-rank")[0]
        # activitiy date
        activity_date = activity.xpath(".//div[@class='entry-head']/time")[0].text.strip()
        activity_date_day, activity_date_time, *_ = activity_date.split(" at ")
        activity_date = human_readable_time_to_machine(activity_date_day)
        for athlete_info in activity.xpath(".//li[@class='entity-details feed-entry']"):
            # athlete info
            activity_athlete, activity_distance, activity_elevation_gain = parse_athlete_activity_info(athlete_info)
            records.add((activity_athlete, activity_date_day, activity_date_time, activity_distance, activity_elevation_gain))
        if last_timestamp < activity_timestamp:
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
    records = set()
    
    # get the recent activity
    club_recent_activity = session_requests.get(f'https://www.strava.com/clubs/{club_id}/recent_activity')
    last_timestamp, temp_records = parse_activity_html(club_recent_activity)
    records.update(temp_records)

    # load more until we can
    while len(temp_records) > 0:
        club_recent_activity_continued = session_requests.get(f"https://www.strava.com/clubs/{club_id}/feed",
            params = dict(feed_type='club', before=last_timestamp, cursor=last_timestamp + ".0")
        )
        last_timestamp, temp_records = parse_activity_html(club_recent_activity_continued)
        records.update(temp_records)

    # close the session
    session_requests.close()

    return {'content' : records}
