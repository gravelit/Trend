# ----------------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------------
import argparse
import coloredlogs
import configparser
import copy
import logging
import os
import pandas
import plotly.express as plot
import plotly.graph_objs as go
import re
import statsmodels.api as stats
import time
from datetime import datetime
from datetime import timedelta

import trello_api

# ----------------------------------------------------------------------------------
# Types
# ----------------------------------------------------------------------------------

coloredlogs.DEFAULT_LEVEL_STYLES['debug'] = {}
coloredlogs.DEFAULT_LEVEL_STYLES['info'] = {'color': 'green'}

class ProjectTrend:
    def __init__(self, project_board):
        self.logger = logging.getLogger(__name__)
        coloredlogs.install(level='INFO')

        # Initialize the API, and grab the project board
        self.logger.info('Requesting project board...')
        self._api = trello_api.TrelloAPI()
        self.project_board = self._api.get_board_with_name(project_board)
        if not self.project_board:
            self.logger.error('Failed to find project board with name {}'.format(project_board))
            raise ValueError()
        self.project_board_id = self.project_board['id']

        # Get the custom field definitions for this board
        self.logger.info('Generating custom field definitions...')
        values = self._api.get_custom_fields(self.project_board_id)
        self.custom_fields = {}
        for value in values:
            self.custom_fields[value['id']] = value['name']

        # Get the label definitions for this board
        self.logger.info('Generating label definitions...')
        values = self._api.get_boards_labels(self.project_board_id)
        self.labels = {}
        for value in values:
            self.labels[value['id']] = value['name']

        # Get the list definitions for this board
        self.logger.info('Generating list definitions...')
        values = self._api.get_boards_lists(self.project_board_id)
        self.lists = {}
        for value in values:
            self.lists[value['id']] = value['name']

        # No cards have been processed yet
        self.cards = []
        self.report_card = None

        # Save name of trend data file
        self._path = os.path.dirname(os.path.realpath(__file__))
        self.trend_data = os.path.join(self._path, 'trend.dat')


    # ------------------------------------------------------------------------------
    def initialize_cards(self):
        card_template = {
            'id': None,
            'name': '',
            'list': '',
            'exclude': False,
        }

        cards = self._api.get_all_cards(self.project_board_id)
        self.logger.info('Total cards: {}'.format(len(cards)))

        self.logger.info('Beginning card processing...')
        cards_processed = 0
        for card in cards:
            new_card = copy.deepcopy(card_template)

            # Save the card ID
            new_card['id'] = card['id']

            # Save the task name
            new_card['name'] = card['name']

            # Save the list the card is on
            new_card['list'] = card['idList']

            # Determine if card should be excluded from remaining calculation
            new_card['exclude'] = self._calculate_exclude(card)

            # Store the custom field data
            values = self._api.get_custom_field_items(new_card['id'])
            for value in values:
                if value['idCustomField'] in self.custom_fields:
                    field = self.custom_fields[value['idCustomField']].lower()
                    new_card[field] = value['value']

            # Save card to class
            self.cards.append(new_card)

            # Logging info
            cards_processed += 1
            if cards_processed % 10 == 0:
                self.logger.info('{} cards have been processed...'.format(cards_processed))

        self.report_card = self.get_card_by_name('Weekly Report')

    # ------------------------------------------------------------------------------
    def add_datapoint(self):
        total_remaining = 0
        for card in self.cards:
            total_remaining += self._get_card_remaining_time(card)

        with open(self.trend_data, 'a') as file:
            now = datetime.now().strftime('%Y-%m-%d')
            file.write('\n{now} = {total}'.format(now=now, total=int(total_remaining)))

    # ------------------------------------------------------------------------------
    def add_trends_to_trello(self):
        if self.report_card:
            id = self.report_card['id']

            # Remove existing attachments
            attachments = self._api.get_all_attachments(id)
            for attachment in attachments:
                self._api.delete_attachment(id, attachment['id'])

            # Add new graphs
            self._api.add_attachment(id, os.path.join(self._path, 'figure.png'), cover=True)
            self._api.add_attachment(id, os.path.join(self._path, 'estimate.png'), cover=False)

    # ------------------------------------------------------------------------------
    def _calculate_exclude(self, trello_card):
        exclude_label = None
        for label in trend.labels:
            if trend.labels[label].lower() == 'exclude':
                exclude_label = label
                break

        for label in trello_card['labels']:
            if label['id'] == exclude_label:
                return True

        complete_list = None
        for list in trend.lists:
            if trend.lists[list].lower() == 'complete':
                complete_list = list
                break

        if trello_card['idList'] == complete_list:
            return True

        return False

    # ------------------------------------------------------------------------------
    def generate_estimated_trend(self, worked_days_per_week):
        self.logger.info('Generating estimated trend data...')
        data_pattern = r'^(?P<date>\d+-\d+-\d+)\s*=\s*(?P<remaining>\d+)\s*$'
        current_dates = []
        current_data = []
        with open(self.trend_data, 'r') as file:
            for line in file:
                match = re.match(data_pattern, line)
                if match:
                    # Collect values
                    current_dates.append(match.groupdict()['date'])
                    current_data.append(int(match.groupdict()['remaining']))

        # Get the last point in the data
        year, month, day = current_dates[-1].split('-')
        last_date = datetime(year=int(year), month=int(month), day=int(day))
        last_remaining = current_data[-1]

        # Expand the data
        while last_remaining > 0:
            last_date += timedelta(days=7)
            last_remaining -= worked_days_per_week
            if last_remaining < 0:
                last_remaining = 0
            current_dates.append('{0}-{1}-{2}'.format(last_date.year, last_date.month, last_date.day))
            current_data.append(int(last_remaining))

        estimate_data = os.path.join(self._path, 'estimate.dat')
        with open(estimate_data, 'w') as file:
            for i in range(len(current_data)):
                file.write('{date} = {data}\n'.format(date=current_dates[i], data=current_data[i]))

        title = self.project_board['name'] + ' Estimated Trend'

        self.generate_trend('estimate', estimate_data, title)


    # ------------------------------------------------------------------------------
    def generate_trend(self, graph_name='figure', trend_data=None, title=None):
        def custom_legend(graph, legend_swap):
            for i, data in enumerate(graph.data):
                for element in data:
                    if element == 'name':
                        graph.data[i].name = legend_swap[graph.data[i].name]
            return graph

        if not trend_data:
            trend_data = self.trend_data

        if not title:
            title = self.project_board['name'] + ' Trend'

        self.logger.info('Gathering trend data...')
        data_pattern = r'^(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+)\s*=\s*(?P<remaining>\d+)\s*$'
        y_axis = []
        x_axis = []
        x_tick_vals = []
        x_tick_text = []
        y_max = 0
        status = []
        with open(trend_data, 'r') as file:
            for line in file:
                match = re.match(data_pattern, line)
                if match:
                    # Add y-axis value
                    remaining = int(match.groupdict()['remaining'])
                    y_axis.append(remaining)

                    # Find the maximum value on the y-axis
                    if remaining > y_max:
                        y_max = remaining

                    # Add x-axis value
                    date = datetime(year=int(match.groupdict()['year']),
                                    month=int(match.groupdict()['month']),
                                    day=int(match.groupdict()['day']))
                    seconds = time.mktime(date.timetuple())
                    x_axis.append(seconds)

                    # Human readable x-axis values
                    if date.strftime('%B %Y') not in x_tick_text:
                        x_tick_text.append(date.strftime('%B %Y'))
                        x_tick_vals.append(seconds)

                    # Color the point based on the trend:
                    # Green - went down in remaining time
                    # Yellow - stayed the same
                    # Red - went up in remaining time
                    if not status:
                        status.append('start')
                    elif y_axis[-1] < y_axis[-2]:
                        status.append('better')
                    elif y_axis[-1] > y_axis[-2]:
                        status.append('worse')
                    else:
                        status.append('same')

        # Margin for top and bottom of graph
        y_margin = int(y_max * 0.05)

        color_map = {'start': '#000000',
                     'better': '#008450',
                     'same': '#EFB700',
                     'worse': '#B81D13'}

        symbol_map = {'start': 'star',
                     'better': 'arrow-down',
                     'same': 'diamond',
                     'worse': 'arrow-up'}

        legend_map = {'start': 'Start',
                     'better': 'Progress',
                     'same': 'Stagnate',
                     'worse': 'Regress'}

        # Calculate trend line
        self.logger.info('Calculating trend line...')
        line = stats.OLS(y_axis, stats.add_constant(x_axis)).fit().fittedvalues

        # Create data frame
        self.logger.info('Generating data frame...')
        data_frame = pandas.DataFrame({'x':x_axis, 'y':y_axis, 'status':status})

        # Create the main plot
        self.logger.info('Generating graph data...')
        figure = plot.scatter(data_frame=data_frame,
                              x='x',
                              y='y',
                              range_y=[0-y_margin, y_max+y_margin],
                              color='status',
                              color_discrete_map=color_map,
                              symbol='status',
                              symbol_map=symbol_map,
                              title=title,
                              labels={
                                  'x': 'Epoch',
                                  'y': 'Days',
                                  'status': 'Status',
                              },
                              width=1920,
                              height=1080)

        # Change the size of the points
        figure.update_traces(marker=dict(size=9),
                             selector=dict(type='scatter', mode='markers'))

        # Update the legend text
        custom_legend(figure, legend_map)  # Must happen before trend line is added

        # Add the trend line
        figure.add_traces(go.Scatter(x=x_axis,
                                     y=line,
                                     line={'width': 1},
                                     mode='lines',
                                     marker_color='black',
                                     name='Trend'))

        # Change the x-axis labels to month names
        figure.update_xaxes(tickangle=45,
                            tickmode='array',
                            tickvals=x_tick_vals,
                            ticktext=x_tick_text)

        # Update axis names
        figure.update_layout(xaxis_title='Timeline',
                             yaxis_title='Days Remaining')

        # Save graph
        self.logger.info('Exporting graph data...')
        figure.write_image('{}.png'.format(graph_name))
        figure.write_html('{}.html'.format(graph_name))

        self.logger.info('Trend generation complete!')

    # ------------------------------------------------------------------------------
    def get_card_by_name(self, name):
        for card in self.cards:
            if card['name'] == name:
                return self._api.get_card(card['id'])


    # ------------------------------------------------------------------------------
    def _get_card_remaining_time(self, card):
        if not card['exclude']:
            if 'remaining' in card:
                remaining = float(card['remaining']['number'])
            else:
                remaining = float(1)  # Assume 1 day remaining if card does not have a time
        else:
            remaining = float(0)

        return remaining

# ----------------------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------

if __name__ == '__main__':
    # Arguments
    parser = argparse.ArgumentParser(description='Calculate a trend for a given Trello project.')
    parser.add_argument('-a', '--add', action='store_true', default=False,
                        help='add a datapoint to the data file')
    parser.add_argument('-e', '--est', metavar='DAYS', type=int, nargs='?', default=4,
                        help='specifies the amount of days to reduce the remaining time by per week when generating the estimated graph')
    args = parser.parse_args()

    # Configuration
    config = configparser.ConfigParser()
    path_to_config = os.path.dirname(os.path.realpath(__file__))
    config.read(os.path.join(path_to_config, 'project.ini'))

    # Configuration values
    board = config['project']['board']

    # Initialize project trend object
    trend = ProjectTrend(board)
    trend.initialize_cards()

    # Adds a datapoint to the file, should happen weekly
    if args.add:
        trend.add_datapoint()

    # Generate the trend data
    trend.generate_trend()
    trend.generate_estimated_trend(args.est)
    trend.add_trends_to_trello()
