import datetime as dt
import os
import re
import pathlib
import shutil
import humanize
import transmission_rpc as t_rpc


# Global variables
START_TIME = dt.datetime.now()
MARKER_CHAR = '#'
TODAY_DATESTAMP = dt.datetime.now().strftime("%Y-%m-%d")

# Define file system base paths
USER_VOLUME = '/Users/scott/'
SOURCE_VOLUME = os.environ.get('TORBASE')
ARCHIVE_VOLUME = os.environ.get('TORARCHIVE')



#############################################################################################################
def execution_env_is_dev(paths_dict):
    # print(f'{MARKER}')
    print(f'{MARKER_CHAR * 120}')
    print('********* THIS SCRIPT IS BEING EXECUTED IN A DEVELOPMENT ENVIRONMENT *********\n')
    dev_paths_dict = {key: f"{value}__DEV" for key, value in paths_dict.items()}
    for k, v in paths_dict.items():
        print(f'{k.replace("_", " ").title()}:')
        print(f'  PROD:\t {paths_dict[k]}')
        print(f'   DEV:\t {dev_paths_dict[k]}')
    return dev_paths_dict
#############################################################################################################


#############################################################################################################
def get_active_transmission_objects():
    global START_TIME
    log_string = 'Fetching objects from Transmission'
    # logger(logfile_path, 'info', log_string)
    try:
        response = t_rpc.Client(host='localhost', port=9091).get_torrents()
        log_string = 'Connection to Transmission successful!'
        # logger(logfile_path, 'success', log_string)
        objects = []

        # Return empty list if empty response from Transmission
        if not response:
            return objects

        for item in response:
            class_dict = vars(item)
            if not class_dict['fields']['name']:
                continue
            else:
                objects.append(class_dict['fields']['name'])
        return objects

    except Exception as e:
        log_string = f'Error connecting to Transmission. Response:\t {str(e)}. Exiting.'
        # logger(logfile_path, 'failure', log_string)
        # execution_complete(logfile_path, START_TIME, 103)
        exit(0)
#############################################################################################################


#############################################################################################################
def get_fs_objects(source_dir):
    global START_TIME
    try:
        fs_objects = os.listdir(source_dir)
    except Exception as e:
        log_string = f'Failed to read file system. Response:\t {str(e)}. Exiting.'
        print(log_string)
        # logger(logfile_path, 'failure', log_string)
        # execution_complete(logfile_path, START_TIME, 101)
        exit(0)

    if '.DS_Store' in fs_objects:
        fs_objects.remove('.DS_Store')

    if not fs_objects:
        logger(logfile_path, 'failure', 'No file system objects were captured. Exiting.')
        execution_complete(logfile_path, START_TIME, 102)
    else:
        return fs_objects
#############################################################################################################



#############################################################################################################
def main():
    paths_dict = {
        'source_dir': os.path.join(SOURCE_VOLUME, 'zzzNew'),
        'archive_dir': os.path.join(ARCHIVE_VOLUME, 'Media_Archive'),
        'graveyard_dir': os.path.join(ARCHIVE_VOLUME, 'Graveyard'),
        'trash_dir': os.path.join(USER_VOLUME, '.Trashes/501/')
    }
    # trash_dir = os.path.join(USER_VOLUME, '.Trashes/501/')
    my_obj = __file__
    p = pathlib.Path(my_obj)
    version_major = 1

    print(f'\n{MARKER_CHAR * 120}')
    # Environment check

    # Logging Parameters
    log_dir = f'Logs/archive_inactive_objects/v{version_major}'
    log_dir_path = os.path.join(USER_VOLUME, log_dir)
    logfile_path = os.path.join(log_dir_path, f'{TODAY_DATESTAMP}.log')

    # Log Directory Validation

    # Modify filesystem paths if env == dev
    if '__DEV' in str(p.parent):
        paths_dict = execution_env_is_dev(paths_dict)

    print(f"\t\t     Source:\t {paths_dict['source_dir']}")
    print(f"\t\tDestination:\t {paths_dict['archive_dir']}")
    print(f"\t\t      Trash:\t {paths_dict['trash_dir']}")
    print(f'\t\t   Log file:\t {logfile_path}')
    # This is the start

    # Step 1: Collect active Transmission objects
    transmission_objects = get_active_transmission_objects()
    log_string = f'Transmission object count:\t {len(transmission_objects)}'

    # Step 2: Collect file system objects


    # Step 3: De-dupe 2 lists of objects into action list


    # Step 4: If length of action_list is 0, exit
    if not action_list:
        exit(0)

    # Step 5: Loop over action_list, processing each object





    # This is the end
    print(f'\nTotal execution time:\t {humanize.precisedelta(dt.datetime.now() - START_TIME)}')
    print(f'{MARKER_CHAR * 120}\n')
    # exit(0)
#############################################################################################################


if __name__ == "__main__":
    main()
