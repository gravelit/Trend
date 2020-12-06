import requests
import logging
import os
import configparser
import json

class TrelloAPI:
    def __init__(self):
        config = configparser.ConfigParser()
        path_to_config = os.path.dirname(os.path.realpath(__file__))
        config.read(os.path.join(path_to_config, 'trello.ini'))

        self.trello = 'https://api.trello.com'
        self.key = config['api']['key']
        self.token = config['api']['token']


    # ------------------------------------------------------------------------------
    def response_to_json(self, response):
        raw = None
        try:
            raw = response.json()
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return raw


    # ------------------------------------------------------------------------------
    def get_board_with_name(self, name):
        request = '{url}/1/members/me/boards?key={key}&token={token}'.format(url=self.trello,
                                                                             key=self.key,
                                                                             token=self.token)
        response = requests.get(url=request)
        raw = self.response_to_json(response)
        for board in raw:
            if board['name'] == name:
                return board
        return None


    # ------------------------------------------------------------------------------
    def get_board(self, board_id):
        request = '{url}/1/boards/{board}?key={key}&token={token}'.format(url=self.trello,
                                                                          board=board_id,
                                                                          key=self.key,
                                                                          token=self.token)
        response = requests.get(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def get_all_cards(self, board_id):
        request = '{url}/1/boards/{board}/cards?key={key}&token={token}'.format(url=self.trello,
                                                                                board=board_id,
                                                                                key=self.key,
                                                                                token=self.token)
        response = requests.get(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def get_list(self, list_id):
        request = '{url}/1/lists/{list}?key={key}&token={token}'.format(url=self.trello,
                                                                        list=list_id,
                                                                        key=self.key,
                                                                        token=self.token)
        response = requests.get(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def get_all_attachments(self, card_id):
        request = '{url}/1/cards/{card}/attachments?key={key}&token={token}'.format(url=self.trello,
                                                                                    card=card_id,
                                                                                    key=self.key,
                                                                                    token=self.token)
        response = requests.get(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def get_custom_field_items(self, card_id):
        request = '{url}/1/cards/{card}/customFieldItems?key={key}&token={token}'.format(url=self.trello,
                                                                                         card=card_id,
                                                                                         key=self.key,
                                                                                         token=self.token)
        response = requests.get(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def get_custom_fields(self, board_id):
        request = '{url}/1/boards/{board}/customFields?key={key}&token={token}'.format(url=self.trello,
                                                                                       board=board_id,
                                                                                       key=self.key,
                                                                                       token=self.token)
        response = requests.get(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def get_card_checklists(self, card_id):
        request = '{url}/1/cards/{card}/checklists?key={key}&token={token}'.format(url=self.trello,
                                                                                   card=card_id,
                                                                                   key=self.key,
                                                                                   token=self.token)
        response = requests.get(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def get_card(self, card_id):
        request = '{url}/1/cards/{card}?key={key}&token={token}'.format(url=self.trello,
                                                                        card=card_id,
                                                                        key=self.key,
                                                                        token=self.token)
        response = requests.get(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def get_boards_labels(self, board_id):
        request = '{url}/1/boards/{board}/labels?key={key}&token={token}'.format(url=self.trello,
                                                                                 board=board_id,
                                                                                 key=self.key,
                                                                                 token=self.token)
        response = requests.get(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def get_boards_lists(self, board_id):
        request = '{url}/1/boards/{board}/lists?key={key}&token={token}'.format(url=self.trello,
                                                                                 board=board_id,
                                                                                 key=self.key,
                                                                                 token=self.token)
        response = requests.get(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def update_card_custom_field(self, card_id, field_id, value):
        request = '{url}/1/cards/{card}/customField/{field}/item'.format(url=self.trello,
                                                                         card=card_id,
                                                                         field=field_id)
        headers = {'Content-Type': 'application/json'}
        data = json.dumps({'value' : value, 'key': self.key, 'token': self.token})
        response = requests.put(url=request, headers=headers, data=data)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def update_card(self, card_id, item, value):
        request = '{url}/1/cards/{card}?key={key}&token={token}&{item}={value}'.format(url=self.trello,
                                                                                       card=card_id,
                                                                                       key=self.key,
                                                                                       token=self.token,
                                                                                       item=item,
                                                                                       value=value)
        response = requests.put(url=request)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def add_attachment(self, card_id, filename, cover=False):
        files = {'file': (filename, open(filename, 'rb'))}
        request = '{url}/1/cards/{card}/attachments'.format(url=self.trello, card=card_id)
        params = {'key': self.key, 'token': self.token, 'setCover': str(cover).lower()}
        response = requests.post(url=request, params=params, files=files)
        return self.response_to_json(response)


    # ------------------------------------------------------------------------------
    def delete_attachment(self, card_id, attachment_id):
        request = '{url}/1/cards/{card}/attachments/{attachment}?key={key}&token={token}'.format(url=self.trello,
                                                                                                 card=card_id,
                                                                                                 attachment=attachment_id,
                                                                                                 key=self.key,
                                                                                                 token=self.token)
        response = requests.request(method='DELETE', url=request)
        return self.response_to_json(response)
