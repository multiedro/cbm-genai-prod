from typing import List
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine

def buscar_documentos_relevantes(
    pergunta: str,
    limite_resultados: int = 10,
    project_id: str = "collavini-genai-prod",
    location: str = "global",
    engine_id: str = "app-collavini-pdfs-mais-im_1749670720875"
) -> List[str]:

    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )
    client = discoveryengine.SearchServiceClient(client_options=client_options)

    serving_config = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_config"

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        )
    )

    links = []
    next_page_token = None

    while True:
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=pergunta,
            page_size=limite_resultados,
            content_search_spec=content_search_spec,
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO
            ),
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
            page_token=next_page_token
        )

        response = client.search(request)

        for result in response.results:
            document = result.document
            derived_data = document.derived_struct_data
            if derived_data and "link" in derived_data:
                links.append(derived_data["link"])

        next_page_token = response.next_page_token
        if not next_page_token or len(links) >= limite_resultados:
            break

    return links[:limite_resultados]