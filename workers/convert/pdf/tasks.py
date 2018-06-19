import os

from utils.celery_client import celery_app
from workers.base_task import BaseTask
from workers.convert.pdf.pdf import cut_pdf
from workers.convert.pdf.jpg_to_pdf import convert_jpg_to_pdf, pdf_merge


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


class MergeConvertedPdf(BaseTask):

    name = "convert.pdf_merge_converted"

    def execute_task(self):
        work_path = self.get_work_path()
        files = _list_files(work_path, '.converted.pdf')
        pdf_merge(files, work_path + '/merged.pdf')  # TODO incorporate JSON data for the filename and metadatas.


def _list_files(directory, extension):
    return (directory + "/" + f for f in os.listdir(directory) if f.endswith(extension))


SplitPdfTask = celery_app.register_task(SplitPdfTask())
JpgToPdfTask = celery_app.register_task(JpgToPdfTask())
PdfMergeConverted = celery_app.register_task(MergeConvertedPdf())

