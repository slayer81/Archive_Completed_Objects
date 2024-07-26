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
SPACE_CHAR = ' '
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
def check_if_target_exists_at_dest(dest_dir, o):
    dest_object_path = os.path.join(dest_dir, pathlib.PurePosixPath(o).name)
    if os.path.exists(dest_object_path):
        return True
    else:
        return False
#############################################################################################################



#############################################################################################################
def classify_directory_contents(directory_path, contents):
    # List contents of the directory
    # contents = os.listdir(directory_path)

    # Initialize dictionaries to store classifications
    files = []
    directories = []
    symlinks = []

    # Iterate over each item in the directory
    for item in contents:
        # print(f'Processing object:\t {item}')
        item_path = os.path.join(directory_path, item)
        # print(f'      Object path:\t {item_path}')

        if os.path.islink(item_path):
            # print(f'        Object is:\t __SYMLINK__')
            symlinks.append(item)
        elif os.path.isfile(item_path):
            # print(f'        Object is:\t __FILE__')
            files.append(item)
        elif os.path.isdir(item_path):
            # print(f'        Object is:\t __DIRECTORY__')
            directories.append(item)
    return files, directories, symlinks
#############################################################################################################


#############################################################################################################
def get_active_transmission_objects():
    global START_TIME
    log_string = 'Fetching objects from Transmission'
    print(f'{str(dt.datetime.now())}\t {log_string}')
    objects = []
    try:
        response = t_rpc.Client(host='localhost', port=9091).get_torrents()
        # log_string = 'Connection to Transmission successful!'
        # print(f'{str(dt.datetime.now())}\t {log_string}')

        # Return empty list if empty response from Transmission
        if not response:
            return objects

        # print(f'{str(dt.datetime.now())}\t Response:\n\t\t{response}\n\n')

        for item in response:
            class_dict = vars(item)
            # print(f'{str(dt.datetime.now())}\t {class_dict}')
            if not class_dict['fields']['name']:
                continue
            else:
                objects.append(class_dict['fields']['name'])
        return objects

    except Exception as e:
        log_string = f'Error connecting to Transmission. Response:\t {str(e)}. Exiting.'
        print(f'{str(dt.datetime.now())}\t {log_string}')
        # execution_complete(logfile_path, START_TIME, 103)
        exit(0)
#############################################################################################################


#############################################################################################################
def get_fs_objects(source_dir):
    global START_TIME
    log_string = 'Fetching objects from filesystem'
    print(f'{str(dt.datetime.now())}\t {log_string}')
    try:
        fs_objects = os.listdir(source_dir)
    except Exception as e:
        log_string = f'Failed to read file system. Response:\t {str(e)}. Exiting.'
        print(log_string)
        # execution_complete(logfile_path, START_TIME, 101)
        exit(0)

    if '.DS_Store' in fs_objects:
        fs_objects.remove('.DS_Store')

    if not fs_objects:
        log_string = 'No file system objects were captured. Exiting.'
        print(f'{str(dt.datetime.now())}\t\t {log_string}')
        # execution_complete(logfile_path, START_TIME, 102)
        exit(0)
    else:
        return fs_objects
#############################################################################################################


#############################################################################################################
def process_object(obj_full_path, o, dest_path):
    temp_dict = {
        'Target Object': obj_full_path,
        '  Object Stem': o,
        '  Destination': dest_path
    }
    # for k, v in temp_dict.items():
    #     log_string = f'{k}:\t {v}'
    #     print(f'{str(dt.datetime.now())}{SPACE_CHAR * 5} {log_string}')
    if not dest_path.__contains__('Trash'):
        dest_label = re.sub(r'_dir|__DEV', '', dest_path.split('/')[-1])
    else:
        dest_label = 'Trash'

    try:
        shutil.move(obj_full_path, dest_path)
        response_dict = {
            'result': 'success',
            'response': f'Object successfully moved to {dest_label}'
        }
        # return response_dict
    except OSError as e:
        response_dict = {
            'result': 'failed',
            'response': f'Response: {str(e)}'
        }
    return response_dict
#############################################################################################################


#############################################################################################################
def process_symlink(o):
    try:
        os.unlink(o) # Unlinking successful
        response_dict = {
            'result': 'success',
            'response': ''
        }
    except Exception as e: # Unlinking failed
        response_dict = {
            'result': 'failed',
            'response': f'Response: {str(e)}'
        }
    return response_dict
#############################################################################################################


#############################################################################################################
def print_obj_counts(action_list, files, directories, symlinks):
    log_string = f'Total objects to process:\t {len(action_list)}'
    print(f'{str(dt.datetime.now())}\t {log_string}')
    print(f'{str(dt.datetime.now())}\t\t\t {SPACE_CHAR * 7}Symlinks:\t {len(symlinks)}')
    print(f'{str(dt.datetime.now())}\t\t\t {SPACE_CHAR * 10}Files:\t {len(files)}')
    print(f'{str(dt.datetime.now())}\t\t\t {SPACE_CHAR * 4}Directories:\t {len(directories)}')
#############################################################################################################


#############################################################################################################
def print_env(paths_dict):
    print(f"{str(dt.datetime.now())}\t      Source:\t {paths_dict['source_dir']}")
    print(f"{str(dt.datetime.now())}\t Destination:\t {paths_dict['archive_dir']}")
    print(f"{str(dt.datetime.now())}\t       Trash:\t {paths_dict['trash_dir']}")
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

    print(f'\n{MARKER_CHAR * 135}')
    start_string = f'Starting execution of: {__file__}'
    print(f'{str(dt.datetime.now())}\t {start_string}')
    # Environment check

    # Logging Parameters
    log_dir = f'Logs/archive_inactive_objects/v{version_major}'
    log_dir_path = os.path.join(USER_VOLUME, log_dir)
    logfile_path = os.path.join(log_dir_path, f'{TODAY_DATESTAMP}.log')
    #
    # Log Directory Validation
    #
    # Modify filesystem paths if env == dev
    if '__DEV' in str(p.parent):
        paths_dict = execution_env_is_dev(paths_dict)
    print_env(paths_dict)

    # This is the start
    ############################################################################

    # Step 1: Collect active Transmission objects
    ############################################################################
    transmission_objects = get_active_transmission_objects()
    log_string = f'Transmission object count:\t {len(transmission_objects)}'
    print(f'{str(dt.datetime.now())}\t {log_string}')


    # Step 2: Collect file system objects
    ############################################################################
    filesystem_objects = get_fs_objects(paths_dict['source_dir'])
    log_string = f'Filesystem object count:\t {len(filesystem_objects)}'
    print(f'{str(dt.datetime.now())}\t {log_string}')


    # Step 3: De-dupe 2 lists of objects into action list
    ############################################################################
    action_list = [i for i in filesystem_objects if i not in transmission_objects]
    if not action_list:
        log_string = 'Nothing to be done here... Exiting.... '
        print(f'{str(dt.datetime.now())}\t {log_string}')
        exit(0)

    # Step 4: Determine type of each object
    files, directories, symlinks = classify_directory_contents(paths_dict['source_dir'], action_list)
    print_obj_counts(action_list, files, directories, symlinks)


    # Step 5: Loop over action_list, processing each object
    ############################################################################
    num_count = len(action_list)
    counter = 1

    for a in action_list:
        proc_start = dt.datetime.now()
        # obj_type = 'unknown'
        obj_full_path = os.path.join(paths_dict['source_dir'], a)
        obj_archive_full_path = os.path.join(paths_dict['archive_dir'], a)

        # Iteration separation
        print(f'{str(dt.datetime.now())}\t {MARKER_CHAR * 80}')

        log_string = f'Object ({counter} / {num_count}):\t {a}'
        print(f'{str(dt.datetime.now())}\t {log_string}')

        # Check for object in each classification list
        # List 'symlinks'
        if a in symlinks:
            log_string = f'Object type: SYMLINK\t Unlinking ...'
            print(f'{str(dt.datetime.now())}\t\t {log_string}')
            response_dict = process_symlink(obj_full_path)
            if response_dict['result'] == 'success':
                log_string = f'*** SUCCESS *** Object successfully unlinked.'
                print(f'{str(dt.datetime.now())}\t\t {log_string}')
            else:
                log_string = f"*** FAILED *** Response:\t {response_dict['response']}."
                print(f'{str(dt.datetime.now())}\t\t {log_string}')

        # List 'files'
        elif a in files:
            log_string = f'Object type: FILE\t Archiving ...'
            print(f'{str(dt.datetime.now())}\t\t {log_string}')
            # Get object size
            # file_size = os.path.getsize(a)
            file_size = os.path.getsize(obj_full_path)
            if os.path.exists(obj_archive_full_path) and os.path.getsize(obj_archive_full_path) >= file_size:
                log_string = f'Object already exists in archive. Moving to Graveyard ...'
                print(f'{str(dt.datetime.now())}\t\t {log_string}')
                response_dict = process_object(obj_full_path, a, paths_dict['graveyard_dir'])


        # List 'directories'
        elif a in directories:
            log_string = f'Object type: DIRECTORY\t Scrubbing ...'
            print(f'{str(dt.datetime.now())}\t\t {log_string}')

        print(f'{str(dt.datetime.now())}\t\t Processing time:\t\t {humanize.precisedelta(dt.datetime.now() - proc_start)}')
        counter += 1
    ############################################################################
    # This is the end
    log_string = 'Execution completed. Total runtime:'
    print(f'{str(dt.datetime.now())}\t {log_string}\t {humanize.precisedelta(dt.datetime.now() - START_TIME)}')
    print(f'{MARKER_CHAR * 135}\n')
    # exit(0)
#############################################################################################################


if __name__ == "__main__":
    main()
