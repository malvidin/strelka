import io
import os
import zipfile
import zlib

from server import lib


class ScanZip(lib.StrelkaScanner):
    """Extracts files from ZIP archives.

    Options:
        limit: Maximum number of files to extract.
            Defaults to 1000.
        password_file: Location of passwords file for zip archives.
            Defaults to etc/strelka/passwords.txt.
    """
    def init(self):
        self.rainbow_table = []

    def scan(self, file_object, options):
        file_limit = options.get('limit', 1000)
        password_file = options.get('password_file', 'etc/strelka/passwords.txt')

        self.metadata['total'] = {'files': 0, 'extracted': 0}

        try:
            if not self.rainbow_table:
                if os.path.isfile(password_file):
                    with open(password_file, 'r+') as f:
                        for line in f:
                            self.rainbow_table.append(bytes(line.strip(), 'utf-8'))

        except IOError:
            file_object.flags.append(f'{self.scanner_name}::file_read_error')

        with io.BytesIO(file_object.data) as zip_object:
            try:
                with zipfile.ZipFile(zip_object) as zip_file_:
                    name_list = zip_file_.namelist()
                    self.metadata['total']['files'] = len(name_list)
                    for name in name_list:
                        if not name.endswith('/'):
                            if self.metadata['total']['extracted'] >= file_limit:
                                break

                            try:
                                child_file = None
                                zinfo = zip_file_.getinfo(name)

                                if zinfo.flag_bits & 0x1 and self.rainbow_table:  # File is encrypted
                                    for pwd in self.rainbow_table:
                                        try:
                                            child_file = zip_file_.read(name, pwd)

                                            if child_file is not None:
                                                file_object.flags.append(f'{self.scanner_name}::encrypted_archive_file')
                                                break
                                        except RuntimeError:
                                            pass
                                elif zinfo.flag_bits & 0x1 and not self.rainbow_table:  # File is encrypted, no passwords
                                    file_object.flags.append(f'{self.scanner_name}::no_archive_passwords')
                                    return
                                else:
                                    child_file = zip_file_.read(name)

                                if child_file is not None:
                                    child_filename = f'{self.scanner_name}::{name}'
                                    child_fo = lib.StrelkaFile(data=child_file,
                                                               filename=child_filename,
                                                               depth=file_object.depth + 1,
                                                               parent_uid=file_object.uid,
                                                               root_uid=file_object.root_uid,
                                                               parent_hash=file_object.hash,
                                                               root_hash=file_object.root_hash,
                                                               source=self.scanner_name)
                                    self.children.append(child_fo)
                                    self.metadata['total']['extracted'] += 1

                            except NotImplementedError:
                                file_object.flags.append(f'{self.scanner_name}::unsupported_compression')
                            except RuntimeError:
                                file_object.flags.append(f'{self.scanner_name}::runtime_error')
                            except ValueError:
                                file_object.flags.append(f'{self.scanner_name}::value_error')
                            except zlib.error:
                                file_object.flags.append(f'{self.scanner_name}::zlib_error')

            except zipfile.BadZipFile:
                file_object.flags.append(f'{self.scanner_name}::bad_zip_file')
