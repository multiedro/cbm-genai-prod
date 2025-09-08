from google.cloud import discoveryengine
from google.api_core.client_options import ClientOptions


# Caminho para a chave JSON da conta de serviço
GOOGLE_APPLICATION_CREDENTIALS = './chave_collavini.json'


def importDocsDataStore():

    project_id = "collavini-genai-prod"
    location = "global"
    data_store_id = "ds-collavini-arquivos_1727374465843"
    gcs_uri = "gs://collavini-arquivos"

    client_options = ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
    client = discoveryengine.DocumentServiceClient(client_options=client_options)
    parent = client.branch_path(project=project_id, location=location, data_store=data_store_id, branch="default_branch")
    source_documents = [f"{gcs_uri}/*"]

    request = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine.GcsSource(
            input_uris=source_documents, data_schema="content"
        ),

        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )

    # Inicia a operação de importação
    operation = client.import_documents(request=request)

    # Imprime o nome da operação para rastreamento
    path_import_docs = str(operation.operation.name)
    print(f'*************Processo de Importação Foi Iniciado*************')
    print(path_import_docs)

    return "Processado"