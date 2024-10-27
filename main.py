import datetime as dt
import os
import sys
import subprocess
import re
import pathlib
import shutil
from types import NoneType
import humanize as hm
import transmission_rpc as t_rpc
import time

# Version tag
VERSION = 1.0
#############################################################################################################
def load_shell_environment(profile_path="/Users/scott/.bash_profile"):
    # Use subprocess to source the shell profile and print the environment variables
    command = f"source {profile_path} && env"
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable="/usr/local/bin/bash")
    for line in proc.stdout:
        (key, _, value) = line.decode("utf-8").partition("=")
        os.environ[key] = value.strip()
#############################################################################################################

load_shell_environment()

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
USER_VOLUME = pathlib.Path.home()
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

        # if scrubber_dict['result'] not in ['warning', 'failed', 'missing']:
        if scrubber_dict['result'] not in ['warning', 'failed']:
            results_dict['continue'] = True
        return results_dict

    else:
        print_string('{:4}{:<24}{:<60}'.format('', 'Is rar archive?:', 'NO'))
        print_string('{:4}{:<24}{:<60}'.format('', 'Next stage:', 'Checking for existing copy in archives'))
        results_dict['continue'] = True
        return results_dict
#############################################################################################################


#############################################################################################################
def instance_check(paths_dict, obj_full_path):
    exists_dict = check_if_object_exists_at_dest(paths_dict['archive_dir'], os.path.basename(obj_full_path))

    if exists_dict['exists'] and exists_dict['action'] == 'graveyard':
        print_string('{:4}{:<24}{:<60}'.format('', 'Archive instance:', 'Similar quality found. Moving to Graveyard'))
        process_object_dict = process_object(obj_full_path, paths_dict['graveyard_dir'])
        print_string('{:4}{:<24}{:<60}'.format('', 'Graveyarding result:', process_object_dict['result'].upper()))
        if process_object_dict['result'] == 'failed':
            print_string('{:4}{:<24}{:<60}'.format('', 'Graveyarding response:', process_object_dict['response']))
            print_string('{:4}{:<24}{:<60}'.format('', 'Next stage', 'Moving to Trash'))
            trash_dict = process_object(obj_full_path, paths_dict['trash_dir'])
            print_string('{:4}{:<24}{:<60}'.format('', 'Trashing result:', trash_dict['result'].upper()))
            return 'failed'
        return 'success'
    else:
        print_string('{:4}{:<24}{:<60}'.format('', 'Archive instance:', 'None found. Moving to Archive'))
        process_object_dict = process_object(obj_full_path, paths_dict['archive_dir'])
        print_string('{:4}{:<24}{:<60}'.format('', 'Archiving result:', process_object_dict['result'].upper()))
        if process_object_dict['result'] != 'success':
            print_string('{:4}{:<24}{:<60}'.format('', 'Archiving response:', process_object_dict['response']))
            return 'failed'
        return 'success'
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
        print(f'{MARKER_CHAR * 140}')
        print_string(f'Execution completed. Total runtime:\t {hm.precisedelta(dt.datetime.now() - START_TIME)}')
        print(f'{MARKER_CHAR * 140}')
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
        # This is the end
        print_string('{:<28}"{:<60}"'.format('No file system objects fetched   ...Exiting...', ''))
        print(f'{MARKER_CHAR * 140}')
        print_string(f'Execution completed. Total runtime:\t {hm.precisedelta(dt.datetime.now() - START_TIME)}')
        print(f'{MARKER_CHAR * 140}')
        print(f'{MARKER_CHAR * 140}\n')
        sys.exit(0)
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
    sys.stdout.flush()
#############################################################################################################


#############################################################################################################
def list_files_from_rar(archive_path):
    target_list = []
    rar_cmd = '/usr/local/bin/7z l'
    year = str(dt.datetime.now().year)

    objects = os.listdir(archive_path)
    rar_filename = [o for o in objects if o.endswith('.rar')]
    if not rar_filename:
        return None

    rar_filename = ''.join(rar_filename)
    rar_file_full_path = os.path.join(archive_path, rar_filename)
    extract_cmd = f'{rar_cmd} "{rar_file_full_path}"'

    # Extract archive info into list, using 7zip
    output = subprocess.run(
        extract_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Decode and split the output
    output_list = output.stdout.decode('utf-8').split()

    for item in output_list:
        item_full_path = os.path.join(archive_path, item)
        if pathlib.Path(item_full_path).is_file() and pathlib.PurePosixPath(item).suffix != '.rar':
            # print(f'Suffix of {item} is {pathlib.PurePosixPath(item).suffix}')
            target_list.append(item)

    if len(target_list) == 1:
        result = ''.join(target_list)
        if os.path.exists(os.path.join(archive_path, result)):
            return result
        else:
            return {'file': result, 'result': 'missing'}
    else:
        # Check returned value for type. Success returns string. Failure returns list
        return target_list
#############################################################################################################


#############################################################################################################
def list_files_from_rar2(archive_path):
    file_list = []
    rar_cmd = '/usr/local/bin/7z l'
    grep_regex = '\'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} +..... +[0-9]+ +[0-9]+ +.+$\''
    grep_cmd = f'grep -Eo {grep_regex}'
    awk_switch = '\'{for (i=6; i<=NF; i++) printf $i " "; print ""}\''
    awk_switch = '\'{print $6}\''

    objects = os.listdir(archive_path)
    rar_filename = [o for o in objects if o.endswith('.rar')]

    if not rar_filename:
        return None

    # Extract uncompressed filename(s) using 7zip, excluding all the "noise"
    rar_filename = ''.join(rar_filename)
    rar_file_full_path = os.path.join(archive_path, rar_filename)
    extract_cmd = f'{rar_cmd} "{rar_file_full_path}" | {grep_cmd} | awk {awk_switch}'

    output = subprocess.run(
        extract_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Decode and split the output
    output_list = output.stdout.decode('utf-8').split('\n')

    # Clean results
    # Remove any empty list values
    output_list = list(filter(None, output_list))

    # Remove any duplicate list items
    output_list = list(dict.fromkeys(output_list))

    # Trim all leading and trailing whitespace from list items
    output_list = [x.strip(' ') for x in output_list]

    # Remove "files" value from results
    if 'files' in output_list:
        output_list.remove('files')

    if len(output_list) == 1:
        result = ''.join(output_list)
        if os.path.exists(os.path.join(archive_path, result)):
            return result
        else:
            return {'file': result, 'result': 'missing'}
    else:
        # Check returned value for type. Success returns string. Failure returns list
        return output_list
#############################################################################################################


#############################################################################################################
def scrub_directory(obj_full_path):
    # Get name of unpacked file
    target_file = list_files_from_rar(obj_full_path)

    # Check if a list was returned, as this indicates multiple targets
    # if not (isinstance(target_file, str)):
    if isinstance(target_file, list):
        # Check if more than 1 unpacked files exist. If so, just leave
        scrubber_result_dict = {
            'scrub_file': target_file,
            'result': 'warning',
            'response': 'Found more than one video file. Skipping ...'
        }
        return scrubber_result_dict

    # Check if a dict was returned
    if isinstance(target_file, dict):
        scrubber_result_dict = {
            'scrub_file': target_file['file'],
            'result': 'success',
            'response': 'Unpacked file missing. Continue ...'
        }
        return scrubber_result_dict

    # Check if a NoneType was returned
    if isinstance(target_file, NoneType):
        scrubber_result_dict = {
            'scrub_file': '',
            'result': 'success',
            'response': 'No rar file found. Continue ...'
        }
        return scrubber_result_dict

    print_string('{:4}{:<24}{:<60}'.format('', 'File to scrub:', target_file))
    # target_file_full_path = os.path.join(f'"{obj_full_path}"', f'"{target_file}"')
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
            print_string('{:4}{:<24}{:<60}'.format('', 'Scrub file msg:', str(e)))
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
    paths_dict = {
        'source_dir': os.path.join(SOURCE_VOLUME, 'zzzNew'),
        'archive_dir': os.path.join(ARCHIVE_VOLUME, 'Media_Archive'),
        'graveyard_dir': os.path.join(ARCHIVE_VOLUME, 'Graveyard'),
        'trash_dir': os.path.join(USER_VOLUME, '.Trash')
    }
    my_obj = __file__
    p = pathlib.Path(my_obj)
    failed_items_list = []

    print(f'\n{MARKER_CHAR * 140}')
    print(f'{MARKER_CHAR * 140}')
    print_string('{:<23}{:<60}'.format('Starting execution of', __file__))
    print_string(f'{MARKER_CHAR * 107}')
    # Environment ready

    # Modify filesystem paths if env == dev
    if '__DEV' in str(p.parent):
        paths_dict = execution_env_is_dev(paths_dict)
    print_env(paths_dict)

    ####################################################################################################################
    # This is the start
    ####################################################################################################################
    stage_num = 1

    #
    # Stage description: Collect active Transmission objects
    ####################################################################################################################
    transmission_objects = get_active_transmission_objects()
    if transmission_objects == 'empty':
        sys.exit(0)
    print_string('{:<26}  {:<60}'.format('Transmission objects:', len(transmission_objects)))
    stage_num += 1

    #
    # Stage description: Collect file system objects
    ####################################################################################################################
    filesystem_objects = get_fs_objects(paths_dict['source_dir'])
    print_string('{:<26}  {:<60}'.format('Filesystem objects:', len(filesystem_objects)))
    stage_num += 1

    #
    # Stage description: De-dupe 2 lists of objects into action list
    ####################################################################################################################
    action_list = [i for i in filesystem_objects if i not in transmission_objects]
    print_string('{:<26}  {:<60}'.format('Total objects to process:', len(action_list)))
    if not action_list:
        # This is the end
        print_string('{:<28}{:<60}'.format('Nothing to be done here     ...Exiting...', ''))
        print(f'{MARKER_CHAR * 140}')
        print_string(f'Execution completed. Total runtime:\t {hm.precisedelta(dt.datetime.now() - START_TIME)}')
        print(f'{MARKER_CHAR * 140}')
        print(f'{MARKER_CHAR * 140}\n')
        sys.exit(0)
    stage_num += 1

    #
    # Stage description: Classify each object
    ####################################################################################################################
    files, directories, symlinks = classify_directory_contents(paths_dict['source_dir'], action_list)
    print_obj_counts(files, directories, symlinks)
    stage_num += 1

    #
    # Stage description: Loop over action_list, processing each object, by classification type
    ####################################################################################################################
    num_count = len(action_list)
    counter = 1

    for a in action_list:
        # Iteration separation
        print_string(f'{MARKER_CHAR * 100}')
        iter_start = dt.datetime.now()
        obj_full_path = os.path.join(paths_dict['source_dir'], a)

        print_string('{:<12}{:<60}'.format(f'Object ({counter} / {num_count}):\t ', a))
        print_string(f'{MARKER_CHAR * 100}')

        # List 'symlinks'
        ################################################################################################################
        if a in symlinks:
            obj_dtype = 'symlink'
            print_string('{:4}{:<24}{:<60}'.format('', 'Object data type:', obj_dtype.upper()))
            print_string('{:4}{:<24}{:<60}'.format('', 'Next stage:', 'Unlinking'))

            response_dict = process_symlink(obj_full_path)
            print_string('{:4}{:<24}{:<60}'.format('', 'Unlinking result:', response_dict['result'].upper()))
            if response_dict['result'] != 'success':
                print_string('{:4}{:<24}{:<60}'.format('', 'Unlinking response:', response_dict['response']))
                failed_items_list.append([obj_dtype, a])

            print_string(f'Object processing time:\t {hm.precisedelta(dt.datetime.now() - iter_start)}')
            counter += 1

        # List 'files'
        ################################################################################################################
        elif a in files:
            obj_dtype = 'file'
            print_string('{:4}{:<24}{:<60}'.format('', 'Object data type:', obj_dtype.upper()))
            print_string('{:4}{:<24}{:<60}'.format('', 'Next stage:', 'Check if object exists in archive'))

            # Check if there is already a version in target archive
            process_result = instance_check(paths_dict, obj_full_path)
            if process_result == 'failed':
                failed_items_list.append([obj_dtype, a])

            print_string(f'Object processing time:\t {hm.precisedelta(dt.datetime.now() - iter_start)}')
            counter += 1

        # List 'directories'
        ################################################################################################################
        elif a in directories:
            obj_dtype = 'directory'
            print_string('{:4}{:<24}{:<60}'.format('', 'Object data type:', obj_dtype.upper()))

            # If rar file in dir, scrub unpacked file
            process_dir_dict = has_rar(obj_full_path)

            if not process_dir_dict['continue']:
                print_string('{:4}{:<24}{:<60}'.format('', 'Scrubbing result:', f"{process_dir_dict['response']}"))
                print_string(f'Object processing time:\t {hm.precisedelta(dt.datetime.now() - iter_start)}')
                failed_items_list.append([obj_dtype, a])
                counter += 1
                continue

            if process_dir_dict['has_rar']:
                print_string('{:4}{:<24}{:<60}'.format('', 'Scrubbing result:', f"{process_dir_dict['result'].upper()}"))

            print_string('{:4}{:<24}{:<60}'.format('', 'Next stage:', 'Check if object exists in archive'))

            process_result = instance_check(paths_dict, obj_full_path)
            if process_result == 'failed':
                failed_items_list.append([obj_dtype, a])

            print_string(f'Object processing time:\t {hm.precisedelta(dt.datetime.now() - iter_start)}')
            counter += 1
    stage_num += 1

    ####################################################################################################################
    # This is the end
    print(f'{MARKER_CHAR * 140}')
    if failed_items_list:
        print_string('')
        print_string('Failed to archive these objects:')
        for f in failed_items_list:
            print_string('{:4}{:>10}:{:4}{:<60}'.format('', f'{f[0].title()}', '', f'{f[1]}'))
        print_string('')
        print(f'{MARKER_CHAR * 140}')
    print_string(f'Execution completed. Total runtime:\t {hm.precisedelta(dt.datetime.now() - START_TIME)}')
    print(f'{MARKER_CHAR * 140}')
    print(f'{MARKER_CHAR * 140}\n')
########################################################################################################################


########################################################################################################################
if __name__ == "__main__":
    main()
