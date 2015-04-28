#!/usr/bin/env python3
"""Package Index manager for S3 hosted package indexes"""
import argparse
import configparser
import logging
import os
import shutil
import tempfile

import boto.s3
import boto.s3.key

logging.basicConfig(
    format='%(levelname)s [%(module)s:%(lineno)s] %(message)s',
)


def create_index(directory, filename='', root=False):
    """Creates index.html files for the package index"""
    index = os.path.join(directory, 'index.html')
    if root:
        with open(index, 'w') as index_file:
            index_file.writelines((
                '<!DOCTYPE html>\n',
                '<html>\n',
                '  <head>\n',
                '    <title>Simple Index</title>\n',
                '    <meta name="api-version" value="2" />\n',
                '  </head>\n',
                '  <body>\n',
            ))
            for sub_directory in os.listdir(directory):
                if not os.path.isdir(os.path.join(directory, sub_directory)):
                    continue
                index_file.writelines((
                    '    <a href="{0}/">{0}</a>\n'
                    .format(sub_directory),
                    '    <br />\n',
                ))
            index_file.writelines((
                '  </body>\n',
                '</html>\n',
            ))
    elif filename:
        with open(index, 'a') as index_file:
            index_file.writelines((
                '<a href="{0}">{0}</a>\n'.format(filename),
                '<br />\n',
            ))
    else:
        return None
    return index


def ensure_ends_with_slash(string):
    """Returns string with a trailing slash"""
    return (
        string
        if string.endswith('/')
        else '{}/'.format(string)
    )


def load_settings(config_path):
    """Loads settings and returns an ConfigParser object"""
    settings = configparser.ConfigParser(
        defaults={
            's3.bucket': '',
            's3.prefix': 'simple',
            'upload': 'False',
        },
        dict_type=dict,
        default_section='default',
    )
    settings.read((
        '{}.config'.format(__file__),
        '/etc/s3pi/config',
        config_path,
    ))

    if settings.has_section(settings.default_section):
        settings = settings[settings.default_section]
    elif len(settings.sections()):
        settings = settings[settings.sections()[0]]
    else:
        settings.add_section('.{}'.format(settings.default_section))
        settings = settings['.{}'.format(settings.default_section)]

    return settings


def add_new_files_to_index(
        package_directory,
        temp_directory,
        log=logging.getLogger(__name__),
):
    """Adds the specified new files to the cloned package index"""
    modified_files = set()
    for filename in os.listdir(package_directory):
        source_file = os.path.join(
            package_directory,
            filename,
        )
        if not os.path.isfile(source_file):
            continue

        simple_package_directory = os.path.join(
            temp_directory,
            filename.split('-')[0].lower(),
        )
        if not os.path.isdir(simple_package_directory):
            log.debug(
                'Creating package directory "%s"',
                simple_package_directory,
            )
            os.makedirs(simple_package_directory)
            modified_files.add(create_index(temp_directory, root=True))

        log.info(
            'Copying "%s" to "%s"',
            source_file,
            simple_package_directory,
        )
        source_file_existed = os.path.exists(os.path.join(
            simple_package_directory,
            filename,
        ))
        modified_files.add(shutil.copy2(
            source_file,
            simple_package_directory,
        ))
        if not source_file_existed:
            modified_files.add(create_index(
                simple_package_directory,
                filename=filename,
            ))
    modified_files.discard(None)
    return modified_files


def download_from_s3(
        directory,
        settings,
        region='us-east-1',
        log=logging.getLogger(__name__),
):
    """Clones the S3 Package Index into the provided directory"""
    s3_conn = None
    try:
        s3_conn = boto.s3.connect_to_region(region)
    except (
            boto.exception.NoAuthHandlerFound,
    ) as error:
        log.critical(error)
    else:
        s3_prefix = ensure_ends_with_slash(settings.get('s3.prefix'))

        s3_bucket = s3_conn.get_bucket(settings.get('s3.bucket'))

        log.info(
            'Cloning package index from "%s" in "%s" to "%s"',
            s3_prefix,
            s3_bucket.name,
            directory,
        )
        for key in s3_bucket.list(prefix=s3_prefix):
            local_file = os.path.join(
                directory,
                key.name[len(s3_prefix):],
            )
            log.debug(
                'Downloading "%s" from "%s" in "%s"',
                local_file,
                key.name,
                key.bucket.name,
            )
            os.makedirs(
                os.path.dirname(local_file),
                exist_ok=True,
            )
            key.get_contents_to_filename(
                local_file,
            )
    finally:
        if s3_conn:
            s3_conn.close()


def upload_to_s3(
        directory,
        settings,
        modified_files,
        region='us-east-1',
        log=logging.getLogger(__name__),
):
    """Uploads the local directory to the S3 Package Index"""
    s3_conn = None
    try:
        s3_conn = boto.s3.connect_to_region(region)
    except (
            boto.exception.NoAuthHandlerFound,
    ) as error:
        log.critical(error)
    else:
        s3_prefix = ensure_ends_with_slash(settings.get('s3.prefix'))

        s3_bucket = s3_conn.get_bucket(settings.get('s3.bucket'))

        for modified_file in modified_files:
            key = boto.s3.key.Key(
                bucket=s3_bucket,
                name=os.path.join(
                    s3_prefix,
                    modified_file[len(directory)+1:],
                ),
            )
            log.info(
                'Uploading "%s" to "%s" in "%s"',
                modified_file,
                key.name,
                key.bucket.name,
            )
            key.set_contents_from_filename(
                modified_file,
            )
            key.set_acl('public-read')


def main():
    """Main function"""
    args = argparse.ArgumentParser(
        description='Package Index manager for S3 hosted package indexes',
    )
    args.add_argument(
        'package_directory',
        help='Directory containing the packages to be uploaded',
    )
    args.add_argument(
        '--upload',
        action='store_true',
        default=False,
        help='Upload the package index after creating it',
    )
    args.add_argument(
        '--config',
        default=os.path.expanduser('~/.s3pi/config'),
        help='Configuration file to use when uploading',
    )
    args.add_argument(
        '--region',
        default='us-east-1',
        help='Override the region to use for S3 (Default: us-east-1)',
    )
    args.add_argument(
        '--verbose',
        action='store_const',
        default=logging.INFO,
        const=logging.DEBUG,
        help='Increase verbosity',
    )

    args = args.parse_args()

    log = logging.getLogger(__name__)
    log.level = args.verbose

    if not os.path.isdir(args.package_directory):
        raise ValueError('"{}" does not exist'.format(args.package_directory))

    settings = load_settings(args.config)

    temporary_directory = tempfile.TemporaryDirectory()
    modified_files = set()

    if args.upload or settings.getboolean('upload'):
        download_from_s3(
            temporary_directory.name,
            settings,
            region=args.region,
            log=log,
        )

    modified_files.update(add_new_files_to_index(
        args.package_directory,
        temporary_directory.name,
        log=log,
    ))

    if args.upload or settings.getboolean('upload'):
        upload_to_s3(
            temporary_directory.name,
            settings,
            modified_files,
            region=args.region,
            log=log,
        )

    temporary_directory.cleanup()

if __name__ == '__main__':
    main()
