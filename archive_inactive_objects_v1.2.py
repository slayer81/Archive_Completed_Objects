import datetime as dt
import os
import sys
import subprocess
import re
import pathlib
import shutil
import humanize as hm
import transmission_rpc as t_rpc
# from pyparsing import empty

# Global variables
START_TIME = dt.datetime.now()
MARKER_CHAR = '#'
SPACE_CHAR = ' '
ALERT_CHAR = '^'
DASH_CHAR = '-'
EQUAL_CHAR = '='
GT_CHAR = '>'
LT_CHAR = '<'
TODAY_DATESTAMP = dt.datetime.now().strftime("%Y-%m-%d")

# Define file system base paths
USER_VOLUME = '/Users/scott/'
SOURCE_VOLUME = os.getenv('TORBASE')
ARCHIVE_VOLUME = os.getenv('TORARCHIVE')
#############################################################################################################
def execution_env_is_dev(paths_dict):
    print(f'{MARKER_CHAR * 140}')
    print('********* THIS SCRIPT IS BEING EXECUTED IN A DEVELOPMENT ENVIRONMENT *********\n')
    dev_paths_dict = {key: f"{value}__DEV" for key, value in paths_dict.items()}
    for k, v in paths_dict.items():
        print(f'{k.replace("_", " ").title()}:')
        print(f'  PROD:\t {paths_dict[k]}')
        print(f'   DEV:\t {dev_paths_dict[k]}')
    return dev_paths_dict
#############################################################################################################


#############################################################################################################
def check_if_object_exists_at_dest(dest_dir, o):
    # Join Archive dir and object
    dest_object_path = os.path.join(dest_dir, pathlib.PurePosixPath(o).name)

    # Check if version exists
    if os.path.exists(dest_object_path):
        # Version exists, so compare sizes
        # Join Source dir and object
        source_object_path = os.path.join(dest_dir, pathlib.PurePosixPath(o).name)
        compare_dict = compare_size_of_two_objects(source_object_path, dest_object_path)
        exists_dict = {
            'exists': True,
            'type': compare_dict['type'],
            'source_size': compare_dict['obj_size'],
            'dest_size': compare_dict['archive_size'],
            'action': compare_dict['action']
        }
    else:
        exists_dict = {
            'exists': False
        }
    return exists_dict
#############################################################################################################


#############################################################################################################
def classify_directory_contents(directory_path, contents):
    # Classify object prior to processing
    # Initialize dictionaries to store classifications
    files = []
    directories = []
    symlinks = []

    # Iterate over each item in the directory
    for item in contents:
        item_path = os.path.join(directory_path, item)

        if os.path.islink(item_path):
            symlinks.append(item)
        elif os.path.isfile(item_path):
            files.append(item)
        elif os.path.isdir(item_path):
            directories.append(item)
    return files, directories, symlinks
#############################################################################################################


#############################################################################################################
def compare_size_of_two_objects(obj_src, obj_dest):
    if pathlib.Path(obj_src).is_file():
        source_obj_type = 'file'
        source_obj_size = get_file_size(obj_src)
        dest_obj_size = get_file_size(obj_dest)
    else:
        source_obj_type = 'dir'
        source_obj_size = get_directory_size(obj_src)
        dest_obj_size = get_directory_size(obj_dest)

    results_dict = {
        'name': pathlib.PurePosixPath(obj_src).name,
        'type': source_obj_type,
        'obj_size': source_obj_size,
        'archive_size': dest_obj_size
    }
    if dest_obj_size < source_obj_size:
        results_dict['action'] = 'archive'
    else:
        results_dict['action'] = 'graveyard'
    return results_dict
#############################################################################################################


#############################################################################################################
def has_rar(obj_full_path):
    results_dict = {
        'has_rar': False,
        'result': '',
        'response': '',
        'file': '',
        'continue': False
    }

    if any(item.endswith('.rar') for item in os.listdir(obj_full_path)):
        results_dict['has_rar'] = True
        print_string('{:4}{:<24}{:<60}'.format('', 'Is rar archive?:', 'YES'))
        print_string('{:4}{:<24}{:<60}'.format('', 'Next stage:', 'Directory scrubbing'))
        print_string('{:4}{:<24}{:<60}'.format('', 'Detecting scrub file', 'Please wait'))

        scrubber_dict = scrub_directory(obj_full_path)
        results_dict['file'] = scrubber_dict['scrub_file']
        results_dict['result'] = scrubber_dict['result']
        results_dict['response'] = scrubber_dict['response']

        if scrubber_dict['result'] != 'failed':
            results_dict['continue'] = True
        return results_dict

    else:
        print_string('{:4}{:<24}{:<60}'.format('', 'Is rar archive?:', 'NO'))
        print_string('{:4}{:<24}{:<60}'.format('', 'Next stage:', 'Checking for existing copy in archives'))
        results_dict['continue'] = True
        return results_dict
#############################################################################################################


#############################################################################################################
def load_shell_environment(profile_path="/Users/scott/.bash_profile"):
    # Use subprocess to source the shell profile and print the environment variables
    command = f"source {profile_path} && env"
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable="/usr/local/bin/bash")
    for line in proc.stdout:
        (key, _, value) = line.decode("utf-8").partition("=")
        os.environ[key] = value.strip()
#############################################################################################################


#############################################################################################################
def get_active_transmission_objects():
    print_string('{:<28}{:<60}'.format('Action:', 'Fetch objects from Transmission API'))
    objects = []
    try:
        response = t_rpc.Client(host='localhost', port=9091).get_torrents()

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
        # This is the end
        print_string('{:<28}"{:<60}"'.format('API poll attempt failed:', str(e)))
        print_string(f'Execution completed. Total runtime:\t {hm.precisedelta(dt.datetime.now() - START_TIME)}')
        print(f'{MARKER_CHAR * 140}\n')
        sys.exit(0)
#############################################################################################################


#############################################################################################################
def get_file_size(file_path):
    return pathlib.Path(file_path).stat().st_size
#############################################################################################################


#############################################################################################################
def get_directory_size(dir_path):
    return sum(f.stat().st_size for f in pathlib.Path(dir_path).rglob('*') if f.is_file())
#############################################################################################################


#############################################################################################################
def get_fs_objects(source_dir):
    print_string('{:<28}{:<60}'.format('Action:', 'Fetching source filesystem objects'))
    objects = []
    try:
        objects = os.listdir(source_dir)
        objects = [o for o in objects if not o.endswith('.DS_Store')]
    except Exception as e:
        print_string(f'Error reading source filesystem:\t {str(e)}')

    if not objects:
        print_string('No file system objects fetched. Exiting...')
    return objects
#############################################################################################################


#############################################################################################################
def process_object(obj_full_path, dest_path):
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
        os.unlink(o)
        # Unlinking successful
        response_dict = {
            'result': 'success',
            'response': ''
        }
    except Exception as e:
        # Unlinking failed
        response_dict = {
            'result': 'failed',
            'response': f'Response: {str(e)}'
        }
    return response_dict
#############################################################################################################


#############################################################################################################
def print_env(paths_dict):
    print_string('{:>25}{:3}{:<60}'.format('Source:', '', paths_dict['source_dir']))
    print_string('{:>25}{:3}{:<60}'.format('Destination:', '', paths_dict['archive_dir']))
    print_string('{:>25}{:3}{:<60}'.format('Trash:', '', paths_dict['trash_dir']))
    print_string(f'{MARKER_CHAR * 100}')
#############################################################################################################


#############################################################################################################
def print_obj_counts(files, directories, symlinks):
    print_string('{:>30}{:3}{:<60}'.format('Symlinks:', '', len(symlinks)))
    print_string('{:>30}{:3}{:<60}'.format('Files:', '', len(files)))
    print_string('{:>30}{:3}{:<60}'.format('Directories:', '', len(directories)))
#############################################################################################################


#############################################################################################################
def print_string(data):
    print('{:<27}\t {:<}'.format(str(dt.datetime.now()), data))
#############################################################################################################


#############################################################################################################
def list_files_from_rar(archive_path):
    file_list = []
    rar_cmd = '7z l'
    grep_regex = '\'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} +..... +[0-9]+ +[0-9]+ +.+$\''
    grep_cmd = f'grep -Eo {grep_regex}'
    awk_switch = '\'{for (i=6; i<=NF; i++) printf $i " "; print ""}\''

    objects = os.listdir(archive_path)
    rar_filename = [o for o in objects if o.endswith('.rar')]

    if not rar_filename:
        # No rar file exists
        return file_list

    # Extract uncompressed filename(s) using 7zip, excluding all the "noise"
    rar_filename = ''.join(rar_filename)
    rar_file_full_path = os.path.join(archive_path, rar_filename)
    extract_cmd = f'{rar_cmd} "{rar_file_full_path}" | {grep_cmd} | awk {awk_switch}'
    result_list = subprocess.run(
        extract_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).stdout.decode('utf-8').split('\n')

    if not result_list:
        print_string('{:<28}{:<60}'.format('Extraction result:', 'Nothing extracted'))
        return file_list

    # Clean results
    # Remove any empty list values
    result_list = list(filter(None, result_list))

    # Remove any duplicate list items
    result_list = list(dict.fromkeys(result_list))

    # Trim all leading and trailing whitespace from list items
    result_list = [x.strip(' ') for x in result_list]

    # Remove "files" value from results
    result_list.remove('files')

    if len(result_list) == 1:
        results = ''.join(result_list)
        return results
    else:
        # Check returned value for type. Success returns string. Failure returns list
        return result_list
#############################################################################################################


#############################################################################################################
def scrub_directory(obj_full_path):
    """
    '''
    print_string('{:<28}{:<60}'.format('Filesystem object count:', len(filesystem_objects)))
    print_string('{:4}{:<24}{:<60}'.format('', 'Object type:', 'FILE'))
    '''
    """

    # Get name of unpacked file
    target_file = list_files_from_rar(obj_full_path)

    if not (isinstance(target_file, str)):
        # Check if more than 1 unpacked files exist. If so, just leave
        scrubber_result_dict = {
            'scrub_file': target_file,
            'result': 'warning',
            'response': 'Found more than one video file. Skipping ...'
        }
        return scrubber_result_dict

    print_string('{:4}{:<24}{:<60}'.format('', 'File to scrub:', target_file))
    target_file_full_path = os.path.join(obj_full_path, target_file)
    try:
        os.remove(target_file_full_path)
        scrubber_result_dict = {
            'scrub_file': target_file,
            'result': 'success',
            'response': f'Scrubbed {target_file}'
        }
        return scrubber_result_dict

    # File deletion failed
    except Exception as e:
        if str(e).startswith('[Errno 2] No such file or directory'):
            scrubber_result_dict = {
                'scrub_file': target_file,
                'result': 'missing',
                'response': 'File not found'
            }
            return scrubber_result_dict
        else:
            scrubber_result_dict = {
                'scrub_file': target_file,
                'result': 'failed',
                'response': f'Response: {str(e)}'
            }
            return scrubber_result_dict
#############################################################################################################


#############################################################################################################
def main():
    # Setup environment
    load_shell_environment()
    paths_dict = {
        'source_dir': os.path.join(SOURCE_VOLUME, 'zzzNew'),
        'archive_dir': os.path.join(ARCHIVE_VOLUME, 'Media_Archive'),
        'graveyard_dir': os.path.join(ARCHIVE_VOLUME, 'Graveyard'),
        'trash_dir': os.path.join(USER_VOLUME, '.Trash')
    }
    my_obj = __file__
    p = pathlib.Path(my_obj)
    version_major = 1

    print(f'\n{MARKER_CHAR * 140}')
    print(f'{MARKER_CHAR * 140}')
    print_string('{:<23}{:<60}'.format('Starting execution of', __file__))
    print_string(f'{MARKER_CHAR * 107}')
    # Environment ready

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

    ############################################################################
    # This is the start
    ############################################################################
    stage_num = 1
    #
    # Stage description: Collect active Transmission objects
    ############################################################################
    transmission_objects = get_active_transmission_objects()
    if transmission_objects == 'empty':
        sys.exit(0)
    print_string('{:<26}  {:<60}'.format('Transmission objects:', len(transmission_objects)))
    stage_num += 1

    #
    # Stage description: Collect file system objects
    ############################################################################
    filesystem_objects = get_fs_objects(paths_dict['source_dir'])
    print_string('{:<26}  {:<60}'.format('Filesystem objects:', len(filesystem_objects)))
    stage_num += 1

    #
    # Stage description: De-dupe 2 lists of objects into action list
    ############################################################################
    action_list = [i for i in filesystem_objects if i not in transmission_objects]
    print_string('{:<26}  {:<60}'.format('Total objects to process:', len(action_list)))
    if not action_list:
        print_string('Nothing to be done here... Exiting.... ')
        print_string(f'Execution completed. Total runtime:\t {hm.precisedelta(dt.datetime.now() - START_TIME)}')
        print(f'{MARKER_CHAR * 140}\n')
        sys.exit(0)
    stage_num += 1

    #
    # Stage description: Classify each object
    ############################################################################
    files, directories, symlinks = classify_directory_contents(paths_dict['source_dir'], action_list)
    # print_obj_counts(action_list, files, directories, symlinks)
    print_obj_counts(files, directories, symlinks)
    stage_num += 1

    #
    # Stage description: Loop over action_list, processing each object
    ############################################################################
    num_count = len(action_list)
    counter = 1

    for a in action_list:
        # Iteration separation
        print_string(f'{MARKER_CHAR * 100}')
        iter_start = dt.datetime.now()
        obj_full_path = os.path.join(paths_dict['source_dir'], a)
        obj_archive_full_path = os.path.join(paths_dict['archive_dir'], a)

        print_string('{:<12}{:<60}'.format(f'Object ({counter} / {num_count}):\t ', a))
        print_string(f'{MARKER_CHAR * 100}')

        ############################################################################
        if a in symlinks:
            obj_dtype = 'symlink'
            print_string('{:4}{:<24}{:<60}'.format('', 'Object data type:', obj_dtype.upper()))

            print_string('{:4}{:<24}{:<60}'.format('', 'Next stage:', 'Unlinking'))
            response_dict = process_symlink(obj_full_path)
            if response_dict['result'] == 'success':
                print_string(f'\t Unlinking result:\t\t  *** SUCCESS ***')
            else:
                print_string(f'\t Unlinking result:\t\t  *** FAILURE ***')
                print_string(f'\t {ALERT_CHAR * 40}')
            print_string(f'Object processing time:\t {hm.precisedelta(dt.datetime.now() - iter_start)}')

        # List 'files'
        ############################################################################
        elif a in files:
            obj_dtype = 'file'
            print_string('{:4}{:<24}{:<60}'.format('', 'Object data type:', obj_dtype.upper()))
            print_string('{:4}{:<24}{:<60}'.format('', 'Archive status:', 'Checking for existing copy in archives'))

            # Get object size
            file_size = os.path.getsize(obj_full_path)

            # Check if there is already a version in target archive
            if os.path.exists(obj_archive_full_path):
                # Check if the two files are the same
                os.path.samefile(obj_full_path, obj_archive_full_path)

                archived_size = os.path.getsize(obj_archive_full_path)
                print_string('{:4}{:<24}{:<60}'.format('', 'Archived object:', 'YES'))
                print_string('{:8}{:<20}{:<60}'.format('', 'Active object size:', file_size))
                print_string('{:8}{:<20}{:<60}'.format('', 'Archived object size:', archived_size))
                #
                if archived_size < file_size:
                    print_string(f'\t Archived version is of smaller size. Overwriting with active version')
                    response_dict = process_object(obj_archive_full_path, paths_dict['trash_dir'])
                else:
                    print_string(f'\t Archived version is of same or larger size. Moving active version to Graveyard')
            else:
                print_string('{:4}{:<24}{:<60}'.format('', 'Archived object:', 'NO'))
                print_string('{:4}{:<24}{:<60}'.format('', 'Next stage:', 'Archiving'))

        # List 'directories'
        ############################################################################
        elif a in directories:
            obj_dtype = 'directory'
            print_string('{:4}{:<24}{:<60}'.format('', 'Object data type:', obj_dtype.upper()))

            # If rar file in dir, scrub unpacked file
            process_dir_dict = has_rar(obj_full_path)

            if not process_dir_dict['continue'] and process_dir_dict['result'] == 'failed':
                print_string('{:4}{:<24}{:<60}'.format('', 'Scrubbing result:', f"{process_dir_dict['response']}"))
                # print(f'Scrubbing failed.\t {process_dir_dict.items()}')
                print_string(f'Object processing time:\t {hm.precisedelta(dt.datetime.now() - iter_start)}')
                counter += 1
                continue

            # if process_dir_dict['continue'] and process_dir_dict['has_rar']:
            print_string('{:4}{:<24}{:<60}'.format('', 'Scrubbing result:', f"{process_dir_dict['result'].upper()}"))
            print_string('{:4}{:<24}{:<60}'.format('', 'Next stage:', 'Checking for existing instance in archives'))
            exists_dict = check_if_object_exists_at_dest(paths_dict['archive_dir'], a)

            if exists_dict['exists'] and exists_dict['action'] == 'graveyard':
                print_string('{:4}{:<24}{:<60}'.format('', 'Instance check:', 'Similar quality found. Moving to Graveyard'))
                process_object_dict = process_object(obj_full_path, paths_dict['graveyard_dir'])
                print_string('{:4}{:<24}{:<60}'.format('', 'Graveyarding result:', process_object_dict['result'].upper()))
                if process_object_dict['result'] == 'failed':
                    print_string('{:4}{:<24}{:<60}'.format('', 'Graveyarding response:', process_object_dict['response']))
                    print_string('{:4}{:<24}{:<60}'.format('', 'Next stage', 'Moving to Trash'))
                    # process_object_dict = process_object(obj_full_path, paths_dict['trash_dir'])
                    trash_dict = process_object(obj_full_path, paths_dict['trash_dir'])
                    print_string('{:4}{:<24}{:<60}'.format('', 'Trashing result:', trash_dict['result'].upper()))

            else:
                process_object_dict = process_object(obj_full_path, paths_dict['archive_dir'])
                print_string('{:4}{:<24}{:<60}'.format('', 'Archiving result:', process_object_dict['result'].upper()))






        print_string(f'Object processing time:\t {hm.precisedelta(dt.datetime.now() - iter_start)}')
        counter += 1
    stage_num += 1
    ############################################################################
    # This is the end
    print(f'{MARKER_CHAR * 140}')
    print_string(f'Execution completed. Total runtime:\t {hm.precisedelta(dt.datetime.now() - START_TIME)}')
    print(f'{MARKER_CHAR * 140}')
    print(f'{MARKER_CHAR * 140}\n')
#############################################################################################################


if __name__ == "__main__":
    main()
