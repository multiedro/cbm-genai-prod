import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import subprocess
import os
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import extract_msg

from google.cloud import storage
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from matplotlib.backends.backend_pdf import PdfPages

# Ensure 'Agg' backend is configured for Matplotlib (no graphical display needed)
matplotlib.use('Agg')

# ------------------ GLOBAL VARIABLES ---------------
# Single source and output bucket
SOURCE_BUCKET_NAME = "demo-collavini-dados"

# Pasta de entrada no bucket (e.g., "entrada/")
SOURCE_FOLDER_PREFIX = "Arquivos Docx/"
# Pasta de saída no bucket (e.g., "saida/")
DESTINATION_FOLDER_PREFIX = "Arquivos Pdf/"

# Local temporary directory on worker
TEMP_DIR = "/tmp/dataflow_temp" 

# Docker image used for Dataflow workers, should contain LibreOffice, Python, etc.
DOCKER_IMAGE = "gcr.io/scientific-elf-471213-d6/formats_converter:latest"

# ------------------ HELPER FUNCTIONS ---------------
def get_storage_client():
    """Creates a Google Cloud Storage client."""
    return storage.Client()

def _convert_image_to_pdf(input_file, output_file):
    """Converts an image file (JPG, PNG) to PDF."""
    try:
        img = Image.open(input_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(output_file, resolution=100.0)
        print(f"[IMAGEM Converter] Converted {os.path.basename(input_file)} to PDF at {output_file}")
        return True
    except Exception as e:
        print(f"[IMAGEM Converter] Error converting image {os.path.basename(input_file)} to PDF: {e}")
        return False

def _convert_excel_to_pdf_matplotlib(input_file, output_file):
    """Converts an Excel file to PDF using Pandas and Matplotlib."""
    try:
        excel_file = pd.ExcelFile(input_file)
        with PdfPages(output_file) as pdf:
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                df.fillna("", inplace=True)

                if df.empty:
                    print(f"[XLSX Converter] Sheet '{sheet_name}' in {os.path.basename(input_file)} is empty. Creating blank page in PDF.")
                    fig, ax = plt.subplots(figsize=(letter[0]/72, letter[1]/72))
                    ax.text(0.5, 0.5, f"Sheet: {sheet_name}\n(Empty)",
                            horizontalalignment='center', verticalalignment='center',
                            transform=ax.transAxes, fontsize=16, color='gray')
                    ax.axis('off')
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
                    continue

                col_labels = [str(col) for col in df.columns] if not df.empty else None

                fig, ax = plt.subplots(figsize=(max(10, len(df.columns) * 1.0), max(6, len(df) * 0.25)))
                ax.axis('tight')
                ax.axis('off')

                table = ax.table(cellText=df.values,
                                 colLabels=col_labels,
                                 cellLoc='center',
                                 loc='center')

                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1.2, 1.2)

                plt.title(f'Sheet: {sheet_name}', fontsize=12)
                
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
        print(f"[XLSX Converter] Converted {os.path.basename(input_file)} to PDF at {output_file} using Matplotlib.")
        return True
    except Exception as e:
        print(f"[XLSX Converter] Error converting Excel {os.path.basename(input_file)} to PDF using Matplotlib: {e}")
        return False

def list_gcs_files_recursively(bucket_name, folder_prefix=None):
    """Lists all files in a GCS bucket, optionally within a specific folder prefix.
       If folder_prefix is None, lists all files in the entire bucket recursively."""
    storage_client = get_storage_client()
    bucket = storage_client.bucket(bucket_name.replace("gs://", ""))
    file_paths_info = []

    # If folder_prefix is None, blob.list_blobs() will list all blobs in the bucket.
    # Otherwise, it will list blobs only under that prefix.
    for blob in bucket.list_blobs(prefix=folder_prefix):
        if blob.name.endswith('/'): # Skip directories
            continue
        full_gcs_path = f"gs://{bucket.name}/{blob.name}"
        filename = os.path.basename(blob.name) # Extracts just the file name without its path
        file_extension = os.path.splitext(filename)[1].lower()
        file_paths_info.append((full_gcs_path, blob.name, filename, file_extension))
    return file_paths_info

# ------------------ APACHE BEAM DOFNS ---------------

class ConvertDocDotxToPdf(beam.DoFn):
    def process(self, element):
        input_gcs_path, original_blob_name, filename, file_extension = element
        
        os.makedirs(TEMP_DIR, exist_ok=True)
        local_input_path = os.path.join(TEMP_DIR, filename)
        output_filename = os.path.splitext(filename)[0] + '.pdf'
        local_output_path = os.path.join(TEMP_DIR, output_filename)

        storage_client = get_storage_client()
        bucket = storage_client.bucket(SOURCE_BUCKET_NAME)
        
        output_blob_name_check = os.path.join(DESTINATION_FOLDER_PREFIX, output_filename)
        output_blob_check = bucket.blob(output_blob_name_check)
        if output_blob_check.exists():
            print(f"File already converted and present at destination: {output_blob_name_check}")
            return

        blob = bucket.blob(original_blob_name)

        try:
            blob.download_to_filename(local_input_path)
            print(f"[DOC/DOTX Process] Downloaded {filename} to {local_input_path}")

            comando = [
                'libreoffice',
                '--headless',
                '--convert-to',
                'pdf',
                local_input_path,
                '--outdir',
                TEMP_DIR
            ]
            subprocess.run(comando, check=True, capture_output=True)

            if os.path.exists(local_output_path):
                yield (local_output_path, original_blob_name, output_filename, SOURCE_BUCKET_NAME)
            else:
                print(f"[DOC/DOTX Process] Conversion failed for {filename}: Output file not found at {local_output_path}.")

        except subprocess.CalledProcessError as e:
            print(f"[DOC/DOTX Process] Error converting {filename} with LibreOffice: {e.stderr.decode()}")
        except FileNotFoundError:
            print(f"[DOC/DOTX Process] Error: LibreOffice not found in container for {filename}.")
        except Exception as e:
            print(f"[DOC/DOTX Process] Unexpected error processing {filename}: {str(e)}")
        
        finally:
            if os.path.exists(local_input_path):
                os.remove(local_input_path)

class ConvertJpgPngToPdf(beam.DoFn):
    def process(self, element):
        input_gcs_path, original_blob_name, filename, file_extension = element
        
        os.makedirs(TEMP_DIR, exist_ok=True)
        local_input_path = os.path.join(TEMP_DIR, filename)
        output_filename = os.path.splitext(filename)[0] + '.pdf'
        local_output_path = os.path.join(TEMP_DIR, output_filename)

        storage_client = get_storage_client()
        bucket = storage_client.bucket(SOURCE_BUCKET_NAME)
        blob = bucket.blob(original_blob_name)
        
        try:
            blob.download_to_filename(local_input_path)
            print(f"[JPG/PNG Process] Downloaded {filename} to {local_input_path}")
            if _convert_image_to_pdf(local_input_path, local_output_path):
                yield (local_output_path, original_blob_name, output_filename, SOURCE_BUCKET_NAME)
            else:
                print(f"[JPG/PNG Process] Image conversion failed for {filename}")
        
        except Exception as e:
            print(f"[JPG/PNG Process] Error downloading/converting {filename}: {e}")
        
        finally:
            if os.path.exists(local_input_path):
                os.remove(local_input_path)

class ConvertXlsxToPdf(beam.DoFn):
    def process(self, element):
        input_gcs_path, original_blob_name, filename, file_extension = element
        
        os.makedirs(TEMP_DIR, exist_ok=True)
        local_input_path = os.path.join(TEMP_DIR, filename)
        output_filename = os.path.splitext(filename)[0] + '.pdf'
        local_output_path = os.path.join(TEMP_DIR, output_filename)

        storage_client = get_storage_client()
        bucket = storage_client.bucket(SOURCE_BUCKET_NAME)
        blob = bucket.blob(original_blob_name)
        
        try:
            blob.download_to_filename(local_input_path)
            print(f"[XLSX Process] Downloaded {filename} to {local_input_path}")
            
            comando = [
                'libreoffice',
                '--headless',
                '--convert-to',
                'pdf',
                local_input_path,
                '--outdir',
                TEMP_DIR
            ]
            
            try:
                subprocess.run(comando, check=True, capture_output=True, text=True)
                if os.path.exists(local_output_path):
                    print(f"[XLSX Process] Converted {os.path.basename(local_input_path)} to PDF at {local_output_path} using LibreOffice.")
                    yield (local_output_path, original_blob_name, output_filename, SOURCE_BUCKET_NAME)
                else:
                    print(f"[XLSX Process] LibreOffice conversion failed for {filename}: Output file not found. Falling back to Matplotlib.")
                    if _convert_excel_to_pdf_matplotlib(local_input_path, local_output_path):
                        yield (local_output_path, original_blob_name, output_filename, SOURCE_BUCKET_NAME)
                    else:
                        print(f"[XLSX Process] Matplotlib fallback also failed for {filename}.")

            except subprocess.CalledProcessError as e:
                print(f"[XLSX Process] LibreOffice conversion failed (CalledProcessError) for {filename}: {e.stderr}. Falling back to Matplotlib.")
                if _convert_excel_to_pdf_matplotlib(local_input_path, local_output_path):
                    yield (local_output_path, original_blob_name, output_filename, SOURCE_BUCKET_NAME)
                else:
                    print(f"[XLSX Process] Matplotlib fallback also failed for {filename}.")
            except FileNotFoundError:
                print(f"[XLSX Process] LibreOffice not found in container for {filename}. Falling back to Matplotlib.")
                if _convert_excel_to_pdf_matplotlib(local_input_path, local_output_path):
                    yield (local_output_path, original_blob_name, output_filename, SOURCE_BUCKET_NAME)
                else:
                    print(f"[XLSX Process] Matplotlib fallback also failed for {filename}.")
            
        except Exception as e:
            print(f"[XLSX Process] Unexpected error during initial processing for {filename}: {str(e)}")
        
        finally:
            if os.path.exists(local_input_path):
                os.remove(local_input_path)

class ConvertRtfToPdf(beam.DoFn):
    def process(self, element):
        input_gcs_path, original_blob_name, filename, file_extension = element

        os.makedirs(TEMP_DIR, exist_ok=True)
        local_input_path = os.path.join(TEMP_DIR, filename)
        output_filename = os.path.splitext(filename)[0] + '.pdf'
        local_output_path = os.path.join(TEMP_DIR, output_filename)

        storage_client = get_storage_client()
        bucket = storage_client.bucket(SOURCE_BUCKET_NAME)
        blob = bucket.blob(original_blob_name)

        try:
            blob.download_to_filename(local_input_path)
            print(f"[RTF Process] Downloaded {filename} to {local_input_path}")

            comando = [
                'libreoffice',
                '--headless',
                '--convert-to',
                'pdf',
                local_input_path,
                '--outdir',
                TEMP_DIR
            ]
            subprocess.run(comando, check=True, capture_output=True)

            if os.path.exists(local_output_path):
                yield (local_output_path, original_blob_name, output_filename, SOURCE_BUCKET_NAME)
            else:
                print(f"[RTF Process] RTF conversion failed for {filename}: Output file not found.")

        except subprocess.CalledProcessError as e:
            print(f"[RTF Process] Error converting RTF {filename}: {e.stderr.decode()}")
        except FileNotFoundError:
            print(f"[RTF Process] Error: LibreOffice not found in container for {filename}.")
        except Exception as e:
            print(f"[RTF Process] Unexpected error processing RTF {filename}: {str(e)}")
        
        finally:
            if os.path.exists(local_input_path):
                os.remove(local_input_path)

# NÃO FUNCIONAL
class ConvertDbToPdf(beam.DoFn):
    def process(self, element):
        input_gcs_path, original_blob_name, filename, file_extension = element
        print(f"[DB Process] Warning: Conversion for .db is not directly supported by the current code. Skipping {filename}.")
        pass

class ConvertMsgToPdf(beam.DoFn):
    def process(self, element):
        input_gcs_path, original_blob_name, filename, file_extension = element
        
        os.makedirs(TEMP_DIR, exist_ok=True)
        local_input_path = os.path.join(TEMP_DIR, filename)
        output_filename = os.path.splitext(filename)[0] + '.pdf'
        local_output_path = os.path.join(TEMP_DIR, output_filename)
        storage_client = get_storage_client()
        bucket = storage_client.bucket(SOURCE_BUCKET_NAME)
        blob = bucket.blob(original_blob_name)
        
        try:
           blob.download_to_filename(local_input_path)
           msg = extract_msg.Message(local_input_path)
           
           doc = SimpleDocTemplate(local_output_path, pagesize=letter)
           styles = getSampleStyleSheet()
           story = []
        
           story.append(Paragraph(f"<b>De:</b> {msg.sender}", styles['Normal']))
           story.append(Paragraph(f"<b>Para:</b> {msg.to}", styles['Normal']))
           if msg.cc: story.append(Paragraph(f"<b>Cc:</b> {msg.cc}", styles['Normal']))
           story.append(Paragraph(f"<b>Assunto:</b> {msg.subject}", styles['h2']))
           story.append(Paragraph(f"<b>Data:</b> {msg.date}", styles['Normal']))
           story.append(Spacer(1, 0.2*inch))
           
           body_text = msg.body.replace('\n', '<br/>') if msg.body else "Email content is empty."
           story.append(Paragraph(body_text, styles['Normal']))
        
           if msg.attachments:
               story.append(Spacer(1, 0.4*inch))
               story.append(Paragraph("<b>Attachments:</b>", styles['h3']))
               for attach in msg.attachments:
                   story.append(Paragraph(f"- {attach.longFilename}", styles['Normal']))
        
           doc.build(story)
           print(f"[MSG Process] Converted .msg {filename} to PDF at {local_output_path}")
           yield (local_output_path, original_blob_name, output_filename, SOURCE_BUCKET_NAME)
        except Exception as e:
           print(f"[MSG Process] Error converting .msg {filename}: {e}")
        finally:
           if os.path.exists(local_input_path): os.remove(local_input_path)

class ConvertPptPptxToPdf(beam.DoFn):
    def process(self, element):
        input_gcs_path, original_blob_name, filename, file_extension = element

        os.makedirs(TEMP_DIR, exist_ok=True)
        local_input_path = os.path.join(TEMP_DIR, filename)
        output_filename = os.path.splitext(filename)[0] + '.pdf'
        local_output_path = os.path.join(TEMP_DIR, output_filename)

        storage_client = get_storage_client()
        bucket = storage_client.bucket(SOURCE_BUCKET_NAME)
        blob = bucket.blob(original_blob_name)

        try:
            blob.download_to_filename(local_input_path)
            print(f"[PPT/PPTX Process] Downloaded {filename} to {local_input_path}")

            comando = [
                'libreoffice',
                '--headless',
                '--convert-to',
                'pdf',
                local_input_path,
                '--outdir',
                TEMP_DIR
            ]
            subprocess.run(comando, check=True, capture_output=True)

            if os.path.exists(local_output_path):
                yield (local_output_path, original_blob_name, output_filename, SOURCE_BUCKET_NAME)
            else:
                print(f"[PPT/PPTX Process] PPT/PPTX conversion failed for {filename}: Output file not found.")

        except subprocess.CalledProcessError as e:
            print(f"[PPT/PPTX Process] Error converting PPT/PPTX {filename}: {e.stderr.decode()}")
        except FileNotFoundError:
            print(f"[PPT/PPTX Process] Error: LibreOffice not found in container for {filename}.")
        except Exception as e:
            print(f"[PPT/PPTX Process] Unexpected error processing PPT/PPTX {filename}: {str(e)}")
       
        finally:
            if os.path.exists(local_input_path):
                os.remove(local_input_path)

class UploadAndCleanGCS(beam.DoFn):
    def process(self, element):
        local_pdf_path, original_blob_name, output_filename, source_bucket_used = element
        
        storage_client = get_storage_client()
        
        destination_bucket = storage_client.bucket(source_bucket_used)
        
        # Constrói o caminho completo para o destino, incluindo a pasta
        destination_blob_path = os.path.join(DESTINATION_FOLDER_PREFIX, output_filename)
        
        blob_to_upload = destination_bucket.blob(destination_blob_path)
        
        try:
            blob_to_upload.upload_from_filename(local_pdf_path)
            print(f"[Upload/Clean] Uploaded {local_pdf_path} to gs://{source_bucket_used}/{destination_blob_path}.")
            
            # Não remove o arquivo original da pasta de origem, apenas move
            # original_blob = destination_bucket.blob(original_blob_name)
            # original_blob.delete()
            # print(f"[Upload/Clean] Original file gs://{source_bucket_used}/{original_blob_name} removed.")

        except Exception as e:
            print(f"[Upload/Clean] ERROR during upload or removal of original file {original_blob_name}: {e}")

        finally:
            if os.path.exists(local_pdf_path):
                os.remove(local_pdf_path)
                print(f"[Upload/Clean] Temporary local PDF {local_pdf_path} removed.")

# ------------------ MAIN PIPELINE DEFINITION ---------------
def run():
    print("Starting file conversion and original deletion process.")

    job_name_prefix = 'collavini-format-converter'
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    job_name = f'{job_name_prefix}-{timestamp}'

    pipeline_options = PipelineOptions(
        runner='DataflowRunner',
        project='scientific-elf-471213-d6',
        region='us-central1',
        staging_location=f'gs://{SOURCE_BUCKET_NAME}/staging',
        temp_location=f'gs://{SOURCE_BUCKET_NAME}/tmp',
        job_name=job_name,
        worker_machine_type='n1-standard-2',
        num_workers=1,
        max_num_workers=2,
        sdk_container_image=DOCKER_IMAGE,
        use_runner_v2=True,
        save_main_session=True,
        service_account='demo-collavini@scientific-elf-471213-d6.iam.gserviceaccount.com'
    )

    with beam.Pipeline(options=pipeline_options) as p:
        print("Starting file processing...")

        all_files_to_process = list_gcs_files_recursively(SOURCE_BUCKET_NAME, folder_prefix=SOURCE_FOLDER_PREFIX)
        if not all_files_to_process:
            print(f"No files found to process in 'gs://{SOURCE_BUCKET_NAME}/{SOURCE_FOLDER_PREFIX}'.")
            return

        files_pcollection = p | 'CreateFilePCollection' >> beam.Create(all_files_to_process)

        doc_dotx_files = (
            files_pcollection
            | 'FilterDocDotx' >> beam.Filter(lambda f: f[3] in ['.doc', '.dotx', '.docx'])
        )
        jpg_png_files = (
            files_pcollection
            | 'FilterJpgPng' >> beam.Filter(lambda f: f[3] in ['.jpg', '.png'])
        )
        xlsx_files = (
            files_pcollection
            | 'FilterXlsx' >> beam.Filter(lambda f: f[3] in ['.xls', '.xlsx'])
        )
        db_files = (
            files_pcollection
            | 'FilterDb' >> beam.Filter(lambda f: f[3] == '.db')
        )
        msg_files = (
            files_pcollection
            | 'FilterMsg' >> beam.Filter(lambda f: f[3] == '.msg')
        )
        rtf_files = (
            files_pcollection
            | 'FilterRtf' >> beam.Filter(lambda f: f[3] == '.rtf')
        )
        ppt_pptx_files = (
            files_pcollection
            | 'FilterPptPptx' >> beam.Filter(lambda f: f[3] in ['.ppt', '.pptx'])
        )

        converted_doc_dotx = (
            doc_dotx_files
            | 'ConvertDocDotx' >> beam.ParDo(ConvertDocDotxToPdf())
        )
        converted_jpg_png = (
            jpg_png_files
            | 'ConvertJpgPng' >> beam.ParDo(ConvertJpgPngToPdf())
        )
        converted_xlsx = (
            xlsx_files
            | 'ConvertXlsx' >> beam.ParDo(ConvertXlsxToPdf())
        )
        converted_db = (
            db_files
            | 'ConvertDb' >> beam.ParDo(ConvertDbToPdf())
        )
        converted_msg = (
            msg_files
            | 'ConvertMsg' >> beam.ParDo(ConvertMsgToPdf())
        )
        converted_rtf = (
            rtf_files
            | 'ConvertRtf' >> beam.ParDo(ConvertRtfToPdf())
        )
        converted_ppt_pptx = (
            ppt_pptx_files
            | 'ConvertPptPptx' >> beam.ParDo(ConvertPptPptxToPdf())
        )

        all_converted_files = (
            (converted_doc_dotx, converted_jpg_png, converted_xlsx, converted_db,
             converted_msg, converted_rtf, converted_ppt_pptx)
            | 'FlattenAllConvertedResults' >> beam.Flatten()
        )

        all_converted_files | 'UploadAndCleanGCS' >> beam.ParDo(UploadAndCleanGCS())

if __name__ == '__main__':
    run()
    print("Conversion process completed!")