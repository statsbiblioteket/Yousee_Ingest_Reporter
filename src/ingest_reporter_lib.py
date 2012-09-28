# encoding: utf-8
import json
import urllib2
import smtplib
import datetime

from cStringIO import StringIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import Charset
from email.header import Header
from email.generator import Generator

def sendMail(smtpServer, sender, recipient, subject, htmlMessage, textMessage, priority):
    # Override python's weird assumption that utf-8 text should be encoded with
    # base64, and instead use quoted-printable (for both subject and body).  I
    # can't figure out a way to specify QP (quoted-printable) instead of base64 in
    # a way that doesn't modify global state. :-(
    Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')

    # We need to use Header objects here instead of just assigning the strings in
    # order to get our headers properly encoded (with QP).
    # You may want to avoid this if your headers are already ASCII, just so people
    # can read the raw message without getting a headache.
    msg['Subject'] = Header(subject.encode('utf-8'), 'UTF-8').encode()

    # Set X-Priority to high if there are any problemes with the ingest.
    msg['X-Priority'] = priority

    # assume From and To are not UTF-8
    msg['From'] = Header(sender.encode('utf-8'), 'UTF-8').encode()
    msg['To'] = Header(recipient.encode('utf-8'), 'UTF-8').encode()

    # Record the MIME types of both parts - text/plain and text/html.
    # Add support for empty text part
    if not textMessage == '':
        part1 = MIMEText(textMessage.encode('utf-8'), 'plain', 'UTF-8')
    part2 = MIMEText(htmlMessage.encode('utf-8'), 'html', 'UTF-8')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    # Add support for empty text part
    if not textMessage == '':
        msg.attach(part1)

    msg.attach(part2)

    # And here we have to instantiate a Generator object to convert the multipart
    # object to a string (can't use multipart.as_string, because that escapes
    # "From" lines).
    io = StringIO()
    g = Generator(io, False)
    g.flatten(msg)

    # Send the message via local SMTP server.
    s = smtplib.SMTP(smtpServer)
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    s.sendmail(sender, recipient, io.getvalue())
    s.quit()

# function to construct a URL for requesting detailed information on a file
# detail URL example:
# http://canopus:9511/ingestmonitorwebpage/#file=tv3_yousee.2217776400-2040-04-11-19.00.00_2217780000-2040-04-11-20.00.00_ftp.ts&mode=details&period=day
def getDetailUrl(appurl, filename):
    url = appurl
    url += '/#file='
    url += filename
    url += '&mode=details&period=all'
    return url


# function for requesting JSON formatted data from the workflow state monitor
def getData(url):
    data = ''
    request = urllib2.Request(url, headers={"Accept": "application/json"})
    try:
        data = json.loads(urllib2.urlopen(request).read())
    except urllib2.HTTPError, e:
        raise Exception("HTTP error: %d" % e.code)
    except urllib2.URLError, e:
        raise Exception("Network error: %s" % e.reason.args[1])

    return data

# function to compare two objects based on their stateName
def compare_stateName(a, b):
    return cmp(a['stateName'], b['stateName'])

# function to compare two objects based on their name
def compare_name(a, b):
    return cmp(a['entity']['name'], b['entity']['name'])

# construct the HTML part of the report email
def writeHTMLbody(appurl, doneState, stoppedState, failedState, progressState, failedAndInProgress, dayStart, dayEnd):
    """

    """
    html = u'''\
<html>
  <head></head>
  <body>
    <p>Kære Operatør</p>
       <p>
       Hvordan går det med dig? Har du det godt?
       </p><p>
       Jeg har her en rapport over hvordan det er gået med opsamling af YouSee
       TV i det seneste døgn. Informationerne i denne mail er alle trukket fra
       <a href="%(url)s">Ingest Monitor websiden</a> som du også selv kan klikke rundt på.
       </p><p>
       Døgnet startede i går klokken %(start)s og varede indtil  dag klokken %(end)s.
       </p>
       <p>
''' % {'url': appurl, 'start': dayStart, 'end': dayEnd}

    html += '<hr>'
    if len(failedState) > 0:
        # add a list of failed files to the report.
        html += u'<h3>Filer som fejlede under import:</h3>'
        html += u'<p>'
        for e in failedState:
            html += u'<a href="' + getDetailUrl(appurl, e['entity']['name']) + '">' \
                    + e['entity']['name'] \
                    + u'</a><br>\n'
        html += u'</p>'
    else:
        html += u'<p>Ingen filer er i en fejltilstand.</p>.'

    html += '<hr>'
    if len(stoppedState) > 0:
        # add a list of failed files to the report.
        html += u'<h3>Filer der er markeret som værende stoppet:</h3>'
        html += u'<p>'
        for e in stoppedState:
            html += u'<a href="' + getDetailUrl(appurl, e['entity']['name']) + '">' \
                    + e['entity']['name'] \
                    + u'</a><br>\n'
        html += u'</p>'
    else:
        html += u'<p>Ingen filer er markeret som stoppet.</p>'

    html += '<hr>'
    if len(progressState) > 0:
        # add a list of files still in progress
        html += u'<h3>Filer som stadig er under behandling eller sat i kø:</h3>'
        html += u'<p>'
        for e in progressState:
            html += u'<a href="' \
                    + getDetailUrl(appurl, e['entity']['name']) \
                    + '">' \
                    + e['component'] \
                    + ', ' \
                    + e['stateName'] \
                    + ', ' \
                    + e['entity']['name'] \
                    + '</a><br>\n'
        html += u'</p>'
    else:
        html += u'<p>Ingen filer bliver processeret eller er i kø.'

    html += '<hr>'
    if len(doneState) > 0:
        # add list of done files to the report
        html += u'<h3>Filer importeret med success:</h3>'
        html += u'<p>'
        for e in doneState:
            html += u'<a href="' + getDetailUrl(appurl, e['entity']['name']) + '">' \
                    + e['entity']['name'] \
                    + u'</a><br>\n'
        html += u'</p>'
    else:
        html += u'<p style="color:red">Ingen filer er blevet importeret med succes i den seneste rapporteringsperiode.</p>'

    if len(failedAndInProgress) > 0:
        # add a list of files still in progress BUT previously were in a FAILED state
        html += u'<h3>Filer bliver behandlet men som har en historisk fejlstatus.</h3>'
        html += u'<p>'
        for e in failedAndInProgress:
            html += u'<a href="'\
                    + getDetailUrl(appurl, e['entity']['name'])\
                    + '">'\
                    + e['component']\
                    + ', '\
                    + e['stateName']\
                    + ', '\
                    + e['entity']['name']\
                    + '</a><br>\n'
        html += u'</p>'
    else:
        html += u'<p>Ingen filer er i fare for uendelig restart-loop.'


    # end the html part of the report
    html += u'''\
        </ul>
    </p>
  </body>
</html>
'''
    return html

# function for constructing the TEXT part of the report email.
def writeTextbody(appurl, doneState, stoppedState, failedState, progressState, dayStart, dayEnd):
    text = u'''\
    Kære Operatør

       Hvordan går det med dig? Har du det godt?

       Jeg har her en rapport over hvordan det er gået med opsamling af YouSee
       TV i det seneste døgn.

       Døgnet startede i går klokken %(start)s og varede indtil  dag klokken %(end)s.

''' % {'start': dayStart, 'end': dayEnd}

    if len(doneState) > 0:
        # add list of done files to the report
        text += u'Filer importeret med success:\n\n'
        for e in doneState:
            text += getDetailUrl(appurl, e['entity']['name']) + '\n'
    else:
        text += u'** INGEN FILER ER BLEVET IMPORTERET MED SUCCES I DEN SENESTE RAPPORTERINGSPERIODE **\n\n'

    if len(failedState) > 0:
        # add a list of failed files to the report.
        text += u'\n\nFiler som fejlede under import:\n\n'
        for e in failedState:
            text += getDetailUrl(appurl, e['entity']['name']) + '\n'
    else:
        text += u'\n\nIngen filer er i en fejltilstand.\n\n'

    if len(stoppedState) > 0:
        # add a list of failed files to the report.
        text += u'\n\nFiler der er markeret som værende stoppet:\n\n'
        for e in stoppedState:
            text += getDetailUrl(appurl, e['entity']['name']) + '\n'
    else:
        text += u'\n\nIngen filer er markeret som stoppet.\n\n'

    if len(progressState) > 0:
        # add a list of files still in progress
        text += u'\n\nFiler som stadig er under behandling eller sat i kø:\n\n'
        for e in progressState:
            text += getDetailUrl(appurl, e['entity']['name']) + '\n'
    else:
        text += u'\n\nIngen filer bliver processeret eller er i kø.\n\n'

    # end the text part of the report
    text += u'''\


'''
    return text

def executeReport(workflowstatemonitorUrl, ingestmonitorwebpageUrl, doneStartTime, recipient, sender, subject, smtpServer):
    # Get a list of all files that have been ingested in the last 24 hours (or,
    # actually, from 'doneStartTime' o'clock yesterday to 24 hours later. Just
    # enough time for a whole season of a really great TV series)
    yesterday=datetime.datetime.now() - datetime.timedelta(days=1)
    startdatetime=datetime.datetime.combine(
        # yesterday's date
        datetime.date(
            yesterday.year,
            yesterday.month,
            yesterday.day),
        # the configured time of day to start. doneStartTime is a list of [hour,minute]
        datetime.time(
            int(doneStartTime[0]),
            int(doneStartTime[1])))

    enddatetime=startdatetime + datetime.timedelta(days=1)

    doneStartDate = startdatetime.isoformat()
    doneEndDate = enddatetime.isoformat()

    # get a list of files in "Done" state. For each file only the last state is
    # requested.
    inDoneState = getData(
        workflowstatemonitorUrl + '/states/?includes=Done&onlyLast=true&startDate=' + doneStartDate + '&endDate=' + doneEndDate)

    # get all files not in Done state regardless of date and time. For each file
    # only the last state is requested.
    notInDoneState = getData(workflowstatemonitorUrl + '/states/?excludes=Done&onlyLast=true')

    # States Stopped and Failed are special, the rest of the of files are
    # considered to be in progress. Progress also includes "Queued" files.
    inStoppedState = [e for e in notInDoneState if e['stateName'] == 'Stopped']
    inFailedState = [e for e in notInDoneState if e['stateName'] == 'Failed']

    # if any files are in the failed state, set the priority of the email to 1 (high)
    # If no files have failed, set the priority to 5 (low)
    if len(inFailedState) > 0:
        emailPriority = '1'
    else:
        emailPriority = '5'

    # gather all files that are not either failed or done. The list is ordered by
    # stateName using the compare_stateName function defined above.
    inProgressState = sorted(
        [e for e in notInDoneState if e['stateName'] != 'Stopped' and e['stateName'] != 'Failed'],
        compare_stateName)

    ## Implementation of the functionality that ensures no failed object will be
    ## overlooked because of automatic restart.
    ## To implement this we compare a set of all objects with a historic "failed" state
    ## with the set of objects currently being processed. The intersection of
    ## these two sets will be included in the report.
    ## To ensure we capture all potential problems, this functionality includes all
    ## historic objects.
    historicFailedState = getData(workflowstatemonitorUrl + '/states/?includes=Failed')

    # Extract a set of object names on objects in progress
    inProgressNames = set(
        [e['entity']['name'] for e in getData(workflowstatemonitorUrl + '/states/?excludes=Done')])

    # Calculate the intersection
    failedAndInProgress = [e for e in historicFailedState if e['entity']['name'] in inProgressNames]


    # Create the body of the message (only an HTML version).
    htmlMessage = writeHTMLbody(
        ingestmonitorwebpageUrl,
        inDoneState,
        inStoppedState,
        inFailedState,
        inProgressState,
        failedAndInProgress,
        startdatetime.strftime("%H.%M"),
        enddatetime.strftime("%H.%M"))

    # In this first release we don not want to include a text version of the email
    textMessage = ""

    sendMail(smtpServer, sender, recipient, subject, htmlMessage, textMessage, emailPriority)
