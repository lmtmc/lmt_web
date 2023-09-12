# todo organize the parameter
# todo px_list not displaying
import os
import time
import json

from dash import dcc, html, Input, Output, State, ALL, MATCH, dash_table, ctx, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from flask_login import current_user

from my_server import app, Job, db
from config import config
from functions import project_function as pf
from views import ui_elements as ui
from views.ui_elements import Session, Runfile, Table, Parameter, Storage

# Constants
PARAMETER_SHOW = {'display': 'block', 'height': '600px'}
TABLE_STYLE = {'overflow': 'auto'}
HIDE_STYLE = {'display': 'none'}
SHOW_STYLE = {'display': 'block'}

# if any of the update_btn get trigged, update the session list

user = 'lmthelpdesk_umass_edu'
# root directory of the session's working area
WORK_LMT = os.environ.get('WORK_LMT', config['path']['work_lmt'])
lmtoy_pid_path = os.environ.get('WORK_LMT', config['path']['work_lmt'])
PID = current_user.username if current_user else None
# default session
init_session = 'session0'
PIS = 0
myFmt = '%Y-%m-%d %H:%M:%S'

column_to_index_mapping = {
    'obsnum': 1,
    '_s': 0,
    'dv': 2,
    'dw': 3,
    'extend': 4,
    'edge': 5,
    'speczoom': 6,
    'srdp': 7,
    'restart': 8,
    'admit': 9
}


def create_session_directory():
    pid_path = os.path.join(WORK_LMT, current_user.username)
    if not os.path.exists(pid_path):
        os.mkdir(pid_path)
    return pid_path


update_btn = [Session.SAVE_BTN.value, Session.CONFIRM_DEL.value,
              Runfile.DEL_BTN.value, Runfile.SAVE_CLONE_RUNFILE_BTN.value]


def check_user_exists():
    return current_user and current_user.is_authenticated


default_data = {'runfile': current_user.username + '_default_runfile'} if check_user_exists() else {'runfile': None}

layout = html.Div(
    [
        html.Div(ui.data_store),
        html.Div(ui.url_location),
        dbc.Row(
            [
                dbc.Col(ui.session_layout, width=4),
                dbc.Col(ui.parameter_layout, width=8),
            ]),

        html.Br(),

    ]
)


# display the sessions
@app.callback(
    [
        Output(Session.SESSION_LIST.value, 'children'),
        Output(Session.MODAL.value, 'is_open'),
        Output(Session.MESSAGE.value, 'children'),
    ],
    [
        Input(Session.NEW_BTN.value, 'n_clicks'),
        Input(Session.SAVE_BTN.value, 'n_clicks'),
        Input(Session.CONFIRM_DEL.value, 'submit_n_clicks'),
        Input(Runfile.CONFIRM_DEL_ALERT.value, 'submit_n_clicks'),
        Input(Parameter.SAVE_ROW_BTN.value, 'n_clicks'),
        Input(Parameter.UPDATE_BTN.value, 'n_clicks'),
        Input(Runfile.SAVE_CLONE_RUNFILE_BTN.value, 'n_clicks'),
        Input(Session.SESSION_LIST.value, 'active_item'),
        Input(Storage.DATA_STORE.value, 'data')
    ],
    [
        State(Runfile.TABLE.value, 'data'),
        State(Session.NAME_INPUT.value, 'value')
    ],
)
def update_session_display(*args):
    n1, n2, n3, n4, n5, n6, n7, active_session, stored_data, table_data, name = args
    triggered_id = ctx.triggered_id

    if not check_user_exists():
        return no_update, no_update, "User is not authenticated"

    pid_path = create_session_directory()
    pid_lmtoy_path = os.path.join(WORK_LMT, 'lmtoy_run', f'lmtoy_{current_user.username}')
    modal_open, message = no_update, ''

    if active_session:
        if triggered_id == Session.NEW_BTN.value:
            modal_open, message = pf.handle_new_session()
        elif triggered_id == Session.SAVE_BTN.value:
            modal_open, message = pf.handle_save_session(init_session, active_session, pid_path, pid_lmtoy_path, name)
        elif triggered_id == Session.CONFIRM_DEL.value:
            message = pf.handle_delete_session(pid_path, active_session)
        if triggered_id in update_btn:
            time.sleep(1)
    else:
        print('Please select a session first!')
    session_list = pf.get_session_list(init_session, pid_path)
    return session_list, modal_open, message


# if click delete button show the confirmation
@app.callback(
    Output(Session.CONFIRM_DEL.value, 'displayed'),
    Input(Session.DEL_BTN.value, 'n_clicks'),
)
def display_confirmation(n_clicks):
    if ctx.triggered_id == Session.DEL_BTN.value:
        return True
    return False


# display selected runfile
@app.callback(
    [
        Output(Runfile.TABLE.value, 'data', allow_duplicate=True),
        # Output(Runfile.TABLE.value, 'columns'),
        Output(Runfile.TABLE.value, 'style_data_conditional'),
        Output(Runfile.CONTENT_TITLE.value, 'children'),
        Output(Runfile.PARAMETER_LAYOUT.value, 'style'),
        Output(Storage.DATA_STORE.value, 'data'),
    ],
    [
        Input({'type': 'runfile-radio', 'index': ALL}, 'value'),
        Input({'type': 'runfile-radio', 'index': ALL}, 'session_name'),
        Input(Runfile.CONFIRM_DEL_ALERT.value, 'submit_n_clicks'),
        Input(Runfile.TABLE.value, "selected_rows"),
    ],
    [
        State(Runfile.TABLE.value, 'data'),
        State(Runfile.TABLE.value, 'columns'),
        State(Storage.DATA_STORE.value, 'data')
    ],
    prevent_initial_call='initial_duplicate'
)
def display_selected_runfile(selected_values, session_name, del_runfile, selRow, existing_data,
                             existing_columns, data_store):
    if not ctx.triggered:
        raise PreventUpdate
    dff = pd.DataFrame(columns=ui.column_list)
    # Initialize default values
    if check_user_exists():
        pid_lmtoy_path = os.path.join(WORK_LMT, 'lmtoy_run', f'lmtoy_{current_user.username}')
        first_runfile = pf.find_runfiles(pid_lmtoy_path, current_user.username)[0]
        df, runfile_title, highlight = pf.initialize_common_variables(
            os.path.join(pid_lmtoy_path, first_runfile), selRow, init_session)
    # Fetching runfile from session
    selected_runfile = pf.get_selected_runfile(ctx, data_store)
    # If a different runfile is selected, reinitialize variables
    if selected_runfile:
        df, runfile_title, highlight = pf.initialize_common_variables(selected_runfile, selRow, init_session)
        data_store['runfile'] = selected_runfile

        if ctx.triggered_id == Runfile.CONFIRM_DEL_ALERT.value:
            pf.del_runfile(selected_runfile)
        dff = pd.concat([df, dff])
    parameter_display = PARAMETER_SHOW  # This seems to be constant, so defined it here
    # print('runfile display', dff)

    return dff.to_dict('records'), highlight, runfile_title, parameter_display, data_store


# Can not edit the default session
# show edit row button after selecting a row
@app.callback(
    [
        Output(Table.NEW_ROW_BTN.value, 'style'),
        Output(Table.EDIT_ROW_BTN.value, 'style'),
        Output(Table.DEL_ROW_BTN.value, 'style'),
        Output(Runfile.DEL_BTN.value, 'style'),
        Output(Runfile.CLONE_BTN.value, 'style'),
        Output(Session.DEL_BTN.value, 'style')
    ],
    [
        Input(Session.SESSION_LIST.value, 'active_item'),
        Input(Runfile.TABLE.value, "selected_rows")
    ],
)
def default_session(active_session, selected_rows):
    if active_session == init_session:
        return [HIDE_STYLE] * 6
    show_or_hide = SHOW_STYLE if active_session and selected_rows else HIDE_STYLE
    hide_delete_session = SHOW_STYLE if active_session and active_session != init_session else HIDE_STYLE
    return show_or_hide, show_or_hide, show_or_hide, SHOW_STYLE, SHOW_STYLE, hide_delete_session


# Define fixed Output objects
fixed_outputs = [
    Output(Parameter.MODAL.value, 'is_open'),
    Output(Runfile.TABLE.value, 'data'),
]
fixed_states = [
    State(Runfile.TABLE.value, 'data'),
]
# Define dynamic Output objects based on a list of field names
field_names = ui.column_list
dynamic_outputs = [Output(field, 'value') for field in field_names]
dynamic_states = [State(field, 'value') for field in field_names]
# Combine fixed and dynamic Output objects

all_outputs = fixed_outputs + dynamic_outputs
all_states = fixed_states + dynamic_states


# display multiply input
def layoutTotable(input_data):
    print(f'input: {input_data}')

    if isinstance(input_data, list):
        output = input_data[0] if len(input_data) == 1 else ",".join(map(str, sorted(input_data)))
    else:
        output = input_data

    print(f'output: {output}')
    return output


def TableToLayout(input):
    output = input
    if ',' in input:
        output = input.split(',')
    return output


# data format need to revise
revise_data = [1, 3, 20, 21, 22, 23, 24]


# todo add more parameters to save
@app.callback(
    all_outputs,
    [
        Input(Table.NEW_ROW_BTN.value, 'n_clicks'),
        Input(Table.EDIT_ROW_BTN.value, 'n_clicks'),
        Input(Table.DEL_ROW_BTN.value, 'n_clicks'),
        Input(Parameter.SAVE_ROW_BTN.value, 'n_clicks'),
        Input(Parameter.UPDATE_BTN.value, 'n_clicks'),
        Input(Runfile.TABLE.value, "selected_rows"),
        Input(Storage.DATA_STORE.value, 'data')],
    all_states,
    prevent_initial_call=True
)
def new_job(n1, n2, n3, n4, n5, selected_row, data, df_data, *state_values):
    # ui.column_list = state_values
    if df_data:
        df = pd.DataFrame(df_data)
        df.fillna('', inplace=True)
    else:
        df = pd.DataFrame(columns=ui.column_list)
    triggered_id = ctx.triggered_id
    output_values = [False] + [''] * (len(ui.column_list) + 1)

    if selected_row is not None and len(selected_row) > 0:
        if triggered_id in [Table.NEW_ROW_BTN.value, Table.EDIT_ROW_BTN.value]:
            selected = df.loc[selected_row[0]]  # Assuming single selection

            # set modal to open and data to remain the same
            output_values[0] = True
            output_values[2:] = [selected[col] for col in ui.column_list]
            output_values[1] = TableToLayout(output_values[1])
            output_values[3] = TableToLayout(output_values[3])
        elif triggered_id == Table.DEL_ROW_BTN.value:
            df.drop(df.index[selected_row[0]], inplace=True)
            pf.save_runfile(df, data['runfile'])
        elif triggered_id in [Parameter.SAVE_ROW_BTN.value, Parameter.UPDATE_BTN.value]:
            # if there are more obsnums then join them using ' '
            print('state_values', state_values)
            parameters = list(state_values)
            for i in revise_data:
                parameters[i] = layoutTotable(state_values[i])

            new_row = {key: value for key, value in zip(ui.column_list, parameters)}

            print('new_row', new_row)
            if triggered_id == Parameter.SAVE_ROW_BTN.value:
                df = df._append(new_row, ignore_index=True)
            else:
                df.iloc[selected_row[0]] = new_row
            pf.save_runfile(df, data['runfile'])
    output_values[1] = df.to_dict('records')

    return output_values


#
#
# if click edit row then show update button in modal, if click new row then show save row button in modal
@app.callback(
    [
        Output(Parameter.SAVE_ROW_BTN.value, 'style'),
        Output(Parameter.UPDATE_BTN.value, 'style')
    ],
    [
        Input(Table.NEW_ROW_BTN.value, 'n_clicks'),
        Input(Table.EDIT_ROW_BTN.value, 'n_clicks')
    ], )
def update_new_btn(n1, n2):
    if ctx.triggered_id == Table.NEW_ROW_BTN.value:
        return SHOW_STYLE, HIDE_STYLE
    if ctx.triggered_id == Table.EDIT_ROW_BTN.value:
        return HIDE_STYLE, SHOW_STYLE
    else:
        return no_update, no_update


# if click delete button show the confirmation
@app.callback(
    Output(Runfile.CONFIRM_DEL_ALERT.value, 'displayed'),
    Input(Runfile.DEL_BTN.value, 'n_clicks'),
    prevent_initial_call=True
)
def display_confirmation(n_clicks):
    return ctx.triggered_id == Runfile.DEL_BTN.value


# open a modal if clone-runfile button
@app.callback(
    [
        Output(Runfile.CLONE_RUNFILE_MODAL.value, 'is_open'),
        Output(Runfile.SAVE_CLONE_RUNFILE_STATUS.value, 'children'),
        Output(Runfile.SAVE_CLONE_RUNFILE_STATUS.value, 'is_open'),
    ],
    [
        Input(Runfile.CLONE_BTN.value, 'n_clicks'),
        Input(Runfile.SAVE_CLONE_RUNFILE_BTN.value, 'n_clicks'),
    ],
    [
        State(Storage.DATA_STORE.value, 'data'),
        State(Runfile.NAME_INPUT.value, 'value'),
    ],

    prevent_initial_call=True
)
def copy_runfile(n1, n2, data_store, new_name):
    modal_open = False
    status = False
    message = ''
    triggered_id = ctx.triggered_id
    if triggered_id == Runfile.CLONE_BTN.value:
        modal_open = True
    if triggered_id == Runfile.SAVE_CLONE_RUNFILE_BTN.value:
        runfile_to_clone = data_store.get('runfile', '')
        new_runfile_name = f"{current_user.username}.{new_name}"
        message, status = pf.clone_runfile(runfile_to_clone, new_runfile_name)
    return modal_open, message, status


# if data['runfile'] submit button
# open a alert to submit
@app.callback(
    [
        Output(Runfile.VALIDATION_ALERT.value, 'is_open'),
        Output(Runfile.VALIDATION_ALERT.value, 'children'),
        Output(Runfile.VALIDATION_ALERT.value, 'color'),
    ],
    Input(Runfile.RUN_BTN.value, 'n_clicks'),
    State(Storage.DATA_STORE.value, 'data'),
    prevent_initial_call=True
)
def submit_runfile(n, data_store):
    if ctx.triggered_id != Runfile.RUN_BTN.value or not data_store.get('runfile'):
        return no_update, no_update, no_update

    message, color = pf.dry_run(data_store['runfile'])
    return True, message, color


# if login get the options for source and obsnums
@app.callback(
    [
        Output(Parameter.SOURCE_DROPDOWN.value, 'options'),
    ],
    [
        Input(Table.NEW_ROW_BTN.value, 'n_clicks'),
        Input(Table.EDIT_ROW_BTN.value, 'n_clicks'),
    ],
    prevent_initial_call=True
)
def update_options(n1, n2):
    if not check_user_exists():
        return no_update

    file_name = '/home/lmt/work_lmt/lmtoy_run/lmtoy_' + current_user.username + '/' + current_user.username + '_source.json'
    with open(file_name, 'r') as json_file:
        data = json.load(json_file)
    # Create options for the dropdown
    options = [{'label': source, 'value': source} for source in data.keys()]
    return [options]


@app.callback(
    Output(Parameter.OBSNUM_DROPDOWN.value, 'options'),
    Input(Parameter.SOURCE_DROPDOWN.value, 'value'),
    prevent_initial_call=True
)
def update_obsnum_options(selected_source):
    if not check_user_exists() or not selected_source:
        return no_update
    file_name = '/home/lmt/work_lmt/lmtoy_run/lmtoy_' + current_user.username + '/' + current_user.username + '_source.json'
    with open(file_name, 'r') as json_file:
        data = json.load(json_file)
    obsnums = data[selected_source]
    options = [{'label': obsnum, 'value': obsnum} for obsnum in obsnums]
    return options