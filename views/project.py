# todo organize the parameter
# todo selected runfile icon visible
import os
import time
import json
import sys

from dash import dcc, html, Input, Output, State, ALL, MATCH, dash_table, ctx, no_update, ClientsideFunction
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from flask_login import current_user

from my_server import app
from config import config
from functions import project_function as pf
from views import ui_elements as ui
from views.ui_elements import Session, Runfile, Table, Parameter, Storage

# Constants
PARAMETER_SHOW = {'display': 'block', 'height': '600px'}
TABLE_STYLE = {'overflow': 'auto'}
HIDE_STYLE = {'display': 'none'}
SHOW_STYLE = {'display': 'block'}

# root directory of the session's working area
default_work_lmt = pf.get_work_lmt_path(config)
default_session_name = os.path.join(default_work_lmt, 'lmtoy_run/lmtoy_')
print('default_work_lmt', default_work_lmt, 'default_session_name', default_session_name)
PID = current_user.username if current_user else None
# default session
init_session = 'session-0'
PIS = 0
myFmt = '%Y-%m-%d %H:%M:%S'

table_column = ui.table_column

# if any of the update_btn get trigged, update the session list
update_btn = [Session.SAVE_BTN.value, Session.CONFIRM_DEL.value,
              Runfile.DEL_BTN.value, Runfile.SAVE_CLONE_RUNFILE_BTN.value]

default_data = {'runfile': current_user.username + '_default_runfile'} if pf.check_user_exists() else {'runfile': None}

layout = html.Div(
    [
        html.Div(ui.data_store),
        html.Div(ui.url_location),
        dbc.Row(
            [
                dbc.Col(ui.session_layout, width=4),
                dbc.Col(ui.parameter_layout, width=8),
                html.Br(),

            ]
        )])


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

    ],
    [
        # State(Storage.DATA_STORE.value, 'data'),
        # State(Runfile.TABLE.value, 'data'),
        State(Session.NAME_INPUT.value, 'value')
    ],
)
def update_session_display(n1, n2, n3, n4, n5, n6, n7, active_session,  name):
    triggered_id = ctx.triggered_id
    if not pf.check_user_exists():
        return no_update, no_update, "User is not authenticated"
    default_pid_path = pf.create_session_directory(default_work_lmt)
    modal_open, message = no_update, ''
    if active_session:
        if active_session != init_session:
            PID = current_user.username
            new_session_path = os.path.join(default_work_lmt, PID, active_session)
            os.environ['WORK_LMT'] = new_session_path
            # pid_path = pf.create_session_directory(new_session_path)
            # pid_lmtoy_path = os.path.join(pid_path, 'lmtoy')
        if triggered_id == Session.NEW_BTN.value:
            modal_open, message = pf.handle_new_session()
        elif triggered_id == Session.SAVE_BTN.value:
            new_session_name = f'Session-{name}'
            modal_open, message = pf.handle_save_session(default_pid_path, new_session_name)
        elif triggered_id == Session.CONFIRM_DEL.value:
            message = pf.handle_delete_session(default_pid_path, active_session)
        if triggered_id in update_btn:
            time.sleep(1)
    else:
        print('Please select a session first!')
    session_list = pf.get_session_list(init_session, default_pid_path)
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
        Output(Runfile.TABLE.value, 'style_data_conditional'),
        Output(Runfile.CONTENT_TITLE.value, 'children'),
        Output(Runfile.PARAMETER_LAYOUT.value, 'style'),
        Output(Storage.DATA_STORE.value, 'data', allow_duplicate=True),
    ],
    [
        Input({'type': 'runfile-radio', 'index': ALL}, 'value'),
        Input(Runfile.CONFIRM_DEL_ALERT.value, 'submit_n_clicks'),
        Input(Parameter.SAVE_ROW_BTN.value, 'n_clicks'),
        Input(Parameter.UPDATE_BTN.value, 'n_clicks'),

    ],
    [
        State(Runfile.TABLE.value, "selected_rows"),
        State(Runfile.TABLE.value, 'data'),
        State(Runfile.TABLE.value, 'columns'),
        State(Storage.DATA_STORE.value, 'data')
    ],
    prevent_initial_call='initial_duplicate'
)
def display_selected_runfile(selected_values, del_runfile, n1, n2, selRow, existing_data,
                             existing_columns, data_store):
    if not ctx.triggered:
        raise PreventUpdate
    dff = pd.DataFrame(columns=table_column)
    highlight = no_update
    runfile_title = ''
    # Initialize default values
    work_lmt = pf.get_work_lmt_path(config)
    if pf.check_user_exists():
        pid_lmtoy_path = pf.get_pid_lmtoy_path(work_lmt, current_user.username)
        # runfiles = pf.find_runfiles(pid_lmtoy_path, current_user.username)
        # if runfiles and len(runfiles) > 0:
        #     first_runfile = runfiles[0]
        #     print('first_runfile', first_runfile)
        #     df, runfile_title, highlight = pf.initialize_common_variables(os.path.join(pid_lmtoy_path, first_runfile),
        #                                                                   selRow, init_session)
    # Fetching runfile from session
    selected_runfile = pf.get_selected_runfile(ctx, data_store)
    if selected_runfile is None:
        selected_runfile = data_store['runfile']
    # If a different runfile is selected, reinitialize variables
    if selected_runfile:
        df, runfile_title, highlight = pf.initialize_common_variables(selected_runfile, selRow, init_session)
        data_store['runfile'] = selected_runfile
        if selRow:
            data_store['selected_row'] = selRow

        if ctx.triggered_id == Runfile.CONFIRM_DEL_ALERT.value:
            pf.del_runfile(selected_runfile)
        dff = pd.concat([df, dff])
    parameter_display = PARAMETER_SHOW  # This seems to be constant, so defined it here
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
    State(Runfile.TABLE.value, "selected_rows"),
    State(Storage.DATA_STORE.value, 'data'),
    State(Runfile.TABLE.value, 'data'),

]
# Define dynamic Output objects based on a list of field names
field_names = table_column
dynamic_outputs = [Output(field, 'value', allow_duplicate=True) for field in field_names]
dynamic_states = [State(field, 'value') for field in field_names]
# Combine fixed and dynamic Output objects

all_outputs = fixed_outputs + dynamic_outputs
all_states = fixed_states + dynamic_states


# todo add more parameters to save
@app.callback(
    all_outputs,
    [
        Input(Table.NEW_ROW_BTN.value, 'n_clicks'),
        Input(Table.EDIT_ROW_BTN.value, 'n_clicks'),
        Input(Table.DEL_ROW_BTN.value, 'n_clicks'),
        Input(Parameter.SAVE_ROW_BTN.value, 'n_clicks'),
        Input(Parameter.UPDATE_BTN.value, 'n_clicks'),
        # Input(Runfile.TABLE.value, "selected_rows"),
        # Input(Storage.DATA_STORE.value, 'data')
    ],
    all_states,
    prevent_initial_call=True,
)
def new_job(n1, n2, n3, n4, n5, selected_row, data, df_data, *state_values):
    if df_data:
        df = pd.DataFrame(df_data)
        df.fillna('', inplace=True)
    else:
        df = pd.DataFrame(columns=table_column)
    triggered_id = ctx.triggered_id
    output_values = [False] + [''] * (len(table_column) + 1)

    if selected_row is not None and len(selected_row) > 0:
        if triggered_id in [Table.NEW_ROW_BTN.value, Table.EDIT_ROW_BTN.value]:
            selected = df.loc[selected_row[0]]  # Assuming single selection

            # set modal to open and data to remain the same
            output_values[0] = True
            output_values[2:] = pf.table_layout([selected[col] for col in table_column])

        elif triggered_id == Table.DEL_ROW_BTN.value:
            df.drop(df.index[selected_row[0]], inplace=True)
            pf.save_runfile(df, data['runfile'])
        elif triggered_id in [Parameter.SAVE_ROW_BTN.value, Parameter.UPDATE_BTN.value]:
            # if there are more obsnums then join them using ' '
            parameters = pf.layout_table(list(state_values))

            new_row = {key: value for key, value in zip(table_column, parameters)}

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
        Output(Storage.DATA_STORE.value, 'data'),
    ],
    [
        Input(Table.NEW_ROW_BTN.value, 'n_clicks'),
        Input(Table.EDIT_ROW_BTN.value, 'n_clicks'),
    ],
    State(Storage.DATA_STORE.value, 'data'),
    prevent_initial_call=True
)
def update_options(n1, n2, stored_data):
    if not pf.check_user_exists():
        return no_update
    # Create options for the dropdown
    json_file_name = default_session_name + current_user.username + '/' + current_user.username + '_source.json'

    if os.path.exists(json_file_name):
        with open(json_file_name, 'r') as json_file:
            data = json.load(json_file)
    #
    # # get default mk_runs.py
    else:
        default_mk_path = default_session_name + current_user.username
        print('path to import mk_runs', default_mk_path)
        sys.path.insert(0, default_mk_path)
        from mk_runs import on
        data = on
        print('on', on)
    source_options = [{'label': source, 'value': source} for source in data.keys()]
    stored_data['source'] = data
    return source_options, stored_data


@app.callback(
    Output(Parameter.OBSNUM_DROPDOWN.value, 'options'),
    Input(Parameter.SOURCE_DROPDOWN.value, 'value'),
    State(Storage.DATA_STORE.value, 'data'),
    prevent_initial_call=True
)
def update_obsnum_options(selected_source, stored_data):
    if not pf.check_user_exists() or not selected_source:
        return no_update
    # file_name = '/home/lmt/work_lmt/lmtoy_run/lmtoy_' + current_user.username + '/' + current_user.username + '_source.json'
    # with open(file_name, 'r') as json_file:
    #     data = json.load(json_file)
    obsnums = stored_data['source'][selected_source]
    options = [{'label': obsnum, 'value': str(obsnum)} for obsnum in obsnums]
    return options


# source and obsnum can't be None
@app.callback(
    Output('source-alert', 'is_open'),
    Output('source-alert', 'children'),
    Input(table_column[0], 'value'),
    Input(table_column[1], 'value'),
)
def source_exist(source, obsnum):
    if source is None:
        return True, 'Please select a source!'
    elif obsnum is None:
        return True, 'Please select one or more obsnum!'
    else:
        return False, ''


@app.callback(
    [
        Output(table_column[3], 'value'),
        Output(table_column[3], 'options'),
    ],
    [
        Input('all-beam', 'n_clicks'),
        Input(table_column[3], 'value')
    ],
    [State(table_column[3], 'options'), ],
    prevent_initial_call=True
)
def select_all_beam(n_clicks, current_values, options):
    all_values = [option['value'] for option in options]

    if ctx.triggered_id == 'all-beam':
        if set(current_values) == set(all_values):  # if all are selected, unselect all
            current_values = []
        else:  # otherwise, select all
            current_values = all_values
    # Apply the strike-through class to selected options
    for option in options:
        if option['value'] in current_values:
            option['label']['props']['className'] = 'strike-through'
        else:
            option['label']['props']['className'] = None

    return current_values, options


# todo modal draggable
app.clientside_callback(
    # ClientsideFunction(namespace='clientside', function_name='make_draggable'),
    '''
    function(is_open) {
    return dash_clientside.clientside.make_draggable(is_open);}
    ''',
    Output("js-container", "children"),
    [Input("draggable-modal", "is_open")],
)

# @app.callback(
#     [Output({'type': 'runfile-radio', 'index': ALL}, 'value'), Output(Runfile.TABLE.value, "selected_rows")],
#     [Input({'type': 'runfile-radio', 'index': ALL}, 'value'), Input(Runfile.TABLE.value, "selected_rows"),]
# )
# def update_table_selections(selected_rows_1, selected_rows_2):
#     # Update both tables' selected rows to keep them synchronized
#     print('selected_runfile', selected_rows_1)
#     print('selected_row', selected_rows_2)
#     return selected_rows_1, selected_rows_1
