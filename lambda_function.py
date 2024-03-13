from datetime import datetime, timedelta
import json
import base64
import os
from email.message import EmailMessage
from google.oauth2 import service_account
from googleapiclient.discovery import build

'''
from googleCalenderApi import sendGoogleCalendar
from googleEmailApi import sendGoogleEmail
from models.BookingInfo import BookingInfo
'''


def lambda_handler(event, context):
    if 'body' not in event or not event['body']:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing request body.'})
        }
    else:
        return perform_action(event)


def perform_action(event):
    try:
        action_type, request_body = parse_request_body(event)

        if action_type == "sendGoogleEmail":
            result = send_google_api_email(request_body)
        elif action_type == "sendGoogleCalendar":
            result = send_google_api_calendar(request_body)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid or missing actionType'})
            }

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': 'Invalid JSON or missing actionType in the request body.'
        }


def parse_request_body(event):
    try:
        # Parse the request body
        request_body = json.loads(event['body'])

        # Retrieve the actionType from the request body
        action_type = request_body.get('actionType')

        if action_type is None or request_body is None:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid or missing actionType'})
            }

        return action_type, request_body

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': 'Invalid JSON or missing actionType in the request body.'
        }


def send_google_api_email(request_body):
    try:
        user_email_address = request_body.get('user_email_address')
        email_text = request_body.get('email_text')

        if user_email_address is None or email_text is None:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid or missing user_email_address or email_text'})
            }
        else:
            token_uri = os.environ['TOKEN_URI']
            client_email = os.environ['CLIENT_EMAIL']
            private_key = os.environ['PRIVATE_KEY'].replace('\\n', '\n')

            # Load the service account credentials directly from the information
            credentials_info = {
                "token_uri": token_uri,
                "client_email": client_email,
                "private_key": private_key
            }

            credentials = service_account.Credentials.from_service_account_info(
                info=credentials_info,
                scopes=["https://mail.google.com/"],
                subject='j-aoussou@gl-navi.co.jp'
            )

            # Build the Gmail API service
            service = build('gmail', 'v1', credentials=credentials)
            # Create an EmailMessage object
            message = EmailMessage()

            # Set email content
            message.set_content(email_text)
            message["To"] = user_email_address
            message["From"] = "j-aoussou@gl-navi.co.jp"
            message["Subject"] = "Japan Wing"

            # Encode the message to base64 URL-safe string
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Create the message payload
            create_message = {"raw": encoded_message}

            # Send the email using Gmail API
            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )

            return {'statusCode': 200, 'message': f'Email sent successfully to {user_email_address}'}

    except Exception as e:
        return {'statusCode': 500, 'error': f'An error occurred: {str(e)}'}


def send_google_api_calendar(request_body):
    try:
        booking_data = request_body.get('booking_data')

        if booking_data is None:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid or missing booking_data'})
            }

        else:

            credentials = get_service_account_credentials_for_google_calender()

            service = build("calendar", "v3", credentials=credentials)

            response = create_google_calender_event(service, booking_data)

            return {
                'statusCode': 201,
                'body': response
            }


    except Exception as e:

        return {'statusCode': 500, 'error': f'booking_data missing from request.'}


def create_google_calender_event(service, booking_data):
    try:

        sessionDuration = calculate_session_duration(booking_data)

        event = {
            'summary': f"{booking_data['sessionType']} with {booking_data['instructorEmail']} and {booking_data['studentEmail']}",
            'location': booking_data['location'],
            'description': booking_data['description'],
            'sessionDuration': sessionDuration,
            'start': {
                'dateTime': booking_data['startTime'],
                'timeZone': booking_data['timeZone'],
            },
            'end': {
                'dateTime': booking_data['endTime'],
                'timeZone': booking_data['timeZone'],
            },
            'attendees': [
                {'email': booking_data['instructorEmail']},
                {'email': booking_data['studentEmail']},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        calendar_id = 'primary'

        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()

        print(f"Event created: {created_event.get('htmlLink')}\n")
        print(f"Event id: {created_event.get('id')}\n")

        return {
            'statusCode': 201,
            'body': json.dumps({
                'message': 'Calendar event created successfully',
                'eventLink': created_event.get('htmlLink'),
                'eventId': created_event.get('id')
            })
        }

    except Exception as e:
        print(f"Error creating google calendar event: {e}")


def get_service_account_credentials_for_google_calender():
    try:
        token_uri = os.environ['TOKEN_URI']
        client_email = os.environ['CLIENT_EMAIL']
        private_key = os.environ['PRIVATE_KEY'].replace('\\n', '\n')

        credentials_info = {
            "token_uri": token_uri,
            "client_email": client_email,
            "private_key": private_key
        }

        credentials = service_account.Credentials.from_service_account_info(
            info=credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar'],
            subject='j-aoussou@gl-navi.co.jp'
        )

        return credentials

    except Exception as e:

        return {'statusCode': 500, 'error': f'An error occurred in get_service_account_credentials: {str(e)}'}


def calculate_session_duration(booking_data):
    # Parse the start and end times
    start_time = datetime.strptime(booking_data['startTime'], '%Y-%m-%dT%H:%M:%S')
    end_time = datetime.strptime(booking_data['endTime'], '%Y-%m-%dT%H:%M:%S')

    # Calculate the duration
    duration = end_time - start_time
    duration_in_hours = duration.total_seconds() / 3600  # Convert seconds to hours
