import os

from utils.celery_client import celery_app

from workers.base_task import BaseTask
from workers.convert.convert_image_pdf import \
    convert_pdf_to_tif, convert_jpg_to_pdf
from workers.convert.convert_image import convert_tif_to_jpg
from workers.convert.convert_pdf import convert_pdf_to_txt, pdf_merge, cut_pdf
from workers.convert.tiff_to_text import tif_to_txt


class SplitPdfTask(BaseTask):
    name = "convert.split_pdf"

    def execute_task(self):
        work_path = self.get_work_path()
        cut_pdf(self.get_param('files_to_split'), work_path, work_path)


class JpgToPdfTask(BaseTask):
    name = "convert.jpg_to_pdf"

    def execute_task(self):
        file = self.get_param("file")
        if file is None:
            raise Exception('NO FILE')
        _, extension = os.path.splitext(file)
        new_file = file.replace(extension, '.converted.pdf')
        convert_jpg_to_pdf(file, new_file)


class TifToJpgTask(BaseTask):
    name = "convert.tif_to_jpg"

    def execute_task(self):
        file = self.get_param('file')
        _, extension = os.path.splitext(file)
        new_file = file.replace(extension, '.jpg')
        convert_tif_to_jpg(file, new_file)


class PdfToTxtTask(BaseTask):
    name = "convert.pdf_to_txt"

    def execute_task(self):
        file = self.get_param('file')
        convert_pdf_to_txt(file, self.get_work_path())


class PdfToTifTask(BaseTask):
    name = "convert.pdf_to_tif"

    def execute_task(self):
        file = self.get_param('file')
        convert_pdf_to_tif(file, self.get_work_path())


class MergeConvertedPdf(BaseTask):
    name = "convert.pdf_merge_converted"

    def execute_task(self):
        work_path = self.get_work_path()
        files = _list_files(work_path, '.converted.pdf')
        pdf_merge(files, work_path + '/merged.pdf')
        # TODO incorporate JSON data for the filename and metadatas.


class TextFromTiffTask(BaseTask):
    name = "convert.tif_to_txt"

    def execute_task(self):
        file_name = self.get_param("file")
        file = os.path.join(self.get_work_path(), file_name)
        tif_to_txt(file, os.path.join(self.get_work_path(), file_name + '.converted.txt'))


def _list_files(directory, extension):
    return (directory + "/" + f for f in os.listdir(directory)
            if f.endswith(extension))


SplitPdfTask = celery_app.register_task(SplitPdfTask())
JpgToPdfTask = celery_app.register_task(JpgToPdfTask())
MergeConvertedPdf = celery_app.register_task(MergeConvertedPdf())
TifToJpgTask = celery_app.register_task(TifToJpgTask())
PdfToTifTask = celery_app.register_task(PdfToTifTask())
PdfToTxtTask = celery_app.register_task(PdfToTxtTask())
TextFromTiffTask = celery_app.register_task(TextFromTiffTask())
