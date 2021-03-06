# strava-google-sheets
This project allows you creating nice statistics graphs for your [Strava club](https://www.strava.com) with [Google Sheets](https://www.google.com/sheets/about/).

Strava is an amazing platform for tracking sport activities. Runners, bikers are using it to measure own progress, save routes and compete. The athletes can join clubs. The clubs are organized by interest or location. Some clubs are tied to a company where club members work. The club is a great way of building up a community. However, clubs have several problems.

- There is no way to see the results of the club members. There are weekly dashboards. It is not possible to view the weekly history. Also, there is a list of all activities in the club.
- It is not possible to create a challenge in the club. For example, a monthly challenge for achieving kilometers, gaining elevation meters or frequency of the training.

These issues have been raised several times by the community, so there might be changes in the future.

## Easy solution

An easy and obvious solution is to build nice dashboards using [Strava API](https://developers.strava.com). Before going into any visualization, I looked into API to [get club activities](https://developers.strava.com/docs/reference/#api-Clubs-getClubActivitiesById). The API returns an array of activities (the example is taken from the official Strava documentation).

```json
[ {
  "resource_state" : 2,
  "athlete" : {
    "resource_state" : 2,
    "firstname" : "Peter",
    "lastname" : "S."
  },
  "name" : "World Championship",
  "distance" : 2641.7,
  "moving_time" : 577,
  "elapsed_time" : 635,
  "total_elevation_gain" : 8.8,
  "type" : "Ride",
  "workout_type" : null
} ]
```

The data is not very helpful. It doesn't contain the date/time of the activity. The athlete complete names are also hidden which might be an obstacle for some purposes.

## Working solution

All right, the solution is to build a web-scrapper that would get all the necessary data from the web-page. The [web-scrapper](lambda_function.py) is implemented in python. And it is executed as an AWS Lambda function.

Data visualization can be done using Google Sheets. The data is written to the Google Sheet by a Google Apps Script. The [script](strava-fetch.gs) calls HTTPS endpoint on AWS and adds the data to the Google Sheet. The script is triggered by a button placed on a sheet.

---

The original idea was to put all the code on Google Apps Script, but the HTML code that is fetched from the Strava web-site cannot be parsed in Google Apps Script.

---

### AWS Lambda setup

The Lambda function is access via AWS API Gateway. In API Gateway, the throttling is limited.

For the AWS Lambda setup, it is required to create a layer containing [lxml](https://lxml.de) library using the ideas from the following resources: [first](https://stackoverflow.com/questions/56818579/unable-to-import-lxml-etree-on-aws-lambda) and [second](https://gist.github.com/allen-munsch/ad8faf9c04b72aa8d0808fa8953bc639).

First, spin off a local container of amazon linux.

```bash
docker run -it amazonlinux:2018.03 bash
```

Install via yum all dependencies when running docker and having already created your virtual environment.

```bash
yum update -y
yum install -y \
  python36 \
  python36-devel \
  python36-virtualenv \
  python34-setuptools \
  gcc \
  gcc-c++ \
  findutils \
  rsync \
  Cython \
  findutils \
  which \
  gzip \
  tar \
  man-pages \
  man \
  wget \
  make \
  zip

# for lxml install two additional libs.
yum install -y \
  libxml2 \
  libxslt

# install lxml in virtualenv.
virtualenv v-env
source v-env/bin/activate
pip install lxml
deactivate

# copy the libs to a zip file
mkdir python
cp -a ./v-env/lib/python3.6/site-packages/. ./python
cp -a ./v-env/lib64/python3.6/site-packages/. ./python
zip -r9 ../layer36.zip python
```

Creata layer using the resulting zip.

The current code also uses a deprecated version of the requests from [boto3](https://github.com/boto/boto3).

### Google sheet example

The Google sheet has several sheets to organize the data:

- **raw data**: this sheet contains data obtained from Strava. This is a table with a header "_Rider_, _Date_, _Time_, _Distance_, _Elevation_". The new records are added to the end of this sheet.

- **stats for month**: this sheet is created using a pivot table for athletes (_Rider_ from the **raw data**) vs kilometers (SUM of _Distance_ from the **raw data**) and elevation gain meters (SUM of _Elevation_ from the **raw data**).

- **stats using calculations**: these are two sheets created using calculations (one for the distance and a second for the elevation). Every sheet consists of two parts. The first part is a table showing all activities in the current month. The second part is a table summing up the results of the activities.

  |     | **A**        | **B** | **C**       |   | **AA**         |
  |-----| ------------ | ----- | ----------- |---| -------------- |
  |**1**| Date         | Time  | *Formula 2* |   | `=D2`          |
  |**2**| *Formula 1*  |       | *Formula 3* |   | `=SUM(D$2:D2)` |

  - The first column gets the dates of all activities `=SORT(FILTER('raw data'!B:C, 'raw data'!B:B > date(2020,3,31),NOT(EQ('raw data'!B:B,"Date"))))` (*Formula 1*).

  - The first row gets the list of all _Rider_ `=TRANSPOSE(UNIQUE('raw data'!A:A))` (*Formula 2*).

  - The data for this table is filled using the query `=IFERROR(QUERY(FILTER('raw data'!$A:$D,'raw data'!$A:$A=D$1,'raw data'!$B:$B=$A2,'raw data'!$C:$C=$B2),"Select Col4"),0)` (*Formula 3*).

- **graphs**: graphs showing the results of athlete progress. I use four graphs:
  
  - for _distance_: (1) total for this month using the Column chart and (2) gaining the distance using Line chart.

  - for _elevation_.: (1) total for this month using the Column chart and (2) gaining the distance using Line chart.

The example sheet for the **stats using calculations** (for _Distance_) will look as follows.

|     | **A**         | **B**   | **C** | **D** | **E** |   | **AA** | **AB** |
|-----| ------------- | ------- | ----- | ----- | ----- |---| ------ | ------ |
|**1**| Date          | Time    | Rider | Alice | Bob   |   | Alice  | Bob    |
|**2**| April 2, 2020 | 6:16 PM |       |     0 | 15.37 |   |      0 |  15.37 |
|**3**| April 4, 2020 | 3:56 PM |       | 37.19 | 23.90 |   |  37.19 |  39.27 |

The graph example is shown below.

![graph-example](graphs-example.png)
