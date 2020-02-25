import requests as req
import json

API = 'http://0.0.0.0:8000/stella/api/v1'


def main():
    r = req.post(API + '/tokens', auth=('participant_a@stella.org', 'pass'))
    r_json = json.loads(r.text)
    token = r_json.get('token')
    r = req.get(API + '/feedbacks', auth=(token, ''))
    # r = req.get(API + '/feedbacks')  # Use this for 'Unauthorized Access'
    print(r.text)


if __name__ == '__main__':
    main()
