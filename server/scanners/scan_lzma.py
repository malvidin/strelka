import io
import lzma

from server import lib


class ScanLzma(lib.StrelkaScanner):
    """Decompresses LZMA files."""
    def scan(self, file_object, options):
        try:
            with io.BytesIO(file_object.data) as lzma_object:
                with lzma.LZMAFile(filename=lzma_object) as lzma_file:
                    try:
                        decompressed_file = lzma_file.read()
                        decompressed_size = len(decompressed_file)
                        self.metadata['decompressedSize'] = decompressed_size
                        child_filename = f'{self.scanner_name}::size_{decompressed_size}'
                        child_fo = lib.StrelkaFile(data=decompressed_file,
                                                   filename=child_filename,
                                                   depth=file_object.depth + 1,
                                                   parent_uid=file_object.uid,
                                                   root_uid=file_object.root_uid,
                                                   parent_hash=file_object.hash,
                                                   root_hash=file_object.root_hash,
                                                   source=self.scanner_name)
                        self.children.append(child_fo)

                    except EOFError:
                        file_object.flags.append(f'{self.scanner_name}::eof_error')

        except lzma.LZMAError:
            file_object.flags.append(f'{self.scanner_name}::lzma_error')
