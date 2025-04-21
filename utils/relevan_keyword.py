from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import pandas as pd
from utils.gemini import call_gemini
import re, os
from datetime import datetime 
import pandas as pd
from sqlalchemy import create_engine, text
from app.core.config import settings
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
# Load environment variables from .env file
load_dotenv()

class About_BQ:
    def __init__(self, project_id: str, credentials_loc: str):
        """
        Inisialisasi koneksi ke BigQuery.
        
        :param project_id: ID proyek Google Cloud.
        :param credentials_loc: Path ke file kredensial JSON.
        """
        self.project_id = project_id
        self.credentials = service_account.Credentials.from_service_account_file(credentials_loc)
        self.client = bigquery.Client(credentials=self.credentials, project=self.project_id)

    def to_pull_data(self, query: str) -> pd.DataFrame:
        """
        Menjalankan query dan mengambil data dari BigQuery sebagai Pandas DataFrame.

        :param query: Query SQL yang akan dijalankan di BigQuery.
        :return: DataFrame hasil query.
        """
        try:
            print("⏳ Menjalankan query ke BigQuery...")
            query_job = self.client.query(query)  # Eksekusi query
            result_df = query_job.to_dataframe()  # Konversi hasil ke DataFrame
            print(f"✅ Query selesai! {len(result_df)} baris data diambil.")
            return result_df
        except Exception as e:
            print(f"❌ Terjadi kesalahan saat mengambil data: {str(e)}")
            return pd.DataFrame()  # Kembalikan DataFrame kosong jika terjadi error    
 
class About_MySQL:
    def __init__(self, db_host, db_port, db_user, db_password, db_name):
        # Membuat engine SQLAlchemy
        self.engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,  # Enable automatic reconnection
            pool_recycle=3600,  # Recycle connections after 1 hour
        )


    def to_pull_data(self, query):
        # Mengambil data menggunakan query yang diberikan dan mengonversinya ke DataFrame
        with self.engine.connect() as connection:
            # Menjalankan query dan mengonversi hasilnya ke DataFrame
            df = pd.read_sql(text(query), connection)
        return df
    
    def to_push_data(self, dataframe: pd.DataFrame, table_name: str, if_exist: str = 'replace'):
        """
        Menyimpan DataFrame ke tabel MySQL.
        
        Parameters:
        - dataframe: pd.DataFrame yang akan disimpan
        - table_name: nama tabel tujuan
        - if_exist: 'replace' untuk mengganti tabel, 'append' untuk menambahkan data
        """
        assert if_exist in ['replace', 'append'], "Parameter 'if_exist' harus 'replace' atau 'append'"
        
        dataframe.to_sql(
            name=table_name,
            con=self.engine,
            if_exists=if_exist,
            index=False,
            method='multi'
        )
        print(f"✅ Data berhasil dipush ke tabel `{table_name}` dengan mode `{if_exist}`.")


def generate_keywords_from_gemini(main_keyword):
    prompt = f"""Saya ingin kamu bertindak sebagai alat pencari keyword yang relevan dan berkaitan erat secara semantik.

Input utama saya adalah: **"{main_keyword}"**

Tugasmu:
1. Kembangkan daftar keyword yang berkaitan erat dengan keyword utama tersebut.
2. Hindari mengulang keyword yang hanya menambahkan kata seperti "perusahaan", "investasi", "teknologi", "startup", "modal ventura", "pendanaan", atau embel-embel lainnya di depan atau belakang keyword utama.
3. Fokus pada keyword yang secara **substansi berbeda**, bukan hanya turunan bentuk dari keyword utama.
4. Keyword bisa berupa nama organisasi yang relevan, institusi regulator, mitra bisnis, sektor industri, program pemerintah, atau istilah populer yang sering dikaitkan.
5. Urutkan dari yang paling relevan ke yang kurang relevan.
6. Gunakan konteks Indonesia terkini.
7. Ambil maksimal **10 keyword**, dalam format array Python.

Contoh input:
"prabowo subianto"

Contoh output:
["prabowo subianto", "presiden RI", "menteri pertahanan", "capres 2024", "ketua gerindra", "koalisi indonesia maju"]

Sekarang, gunakan keyword: **"{main_keyword}"**"""

    response = call_gemini(prompt)

    prediction = eval(re.findall(r'\[.*\]', response.lower(), flags=re.I | re.S)[0])

    prediction.append(main_keyword.lower())
    
    return list(set(prediction))


class ElasticsearchIngestor:
    def __init__(self, host="localhost", port=9200, username=None, password=None):
        self.es = Elasticsearch(
            f"{host}:{port}",
            basic_auth=(username, password) if username and password else None,
            verify_certs=False
        )

    def create_index_if_not_exists(self, index_name: str):
        """
        Create index if it doesn't exist
        """
        if not self.es.indices.exists(index=index_name):
            self.es.indices.create(index=index_name)
            print(f"✅ Created new index: {index_name}")

    def to_ingest(self, data: [], index_name: str, id_field: str = None):
        """
        Mengirim data dari DataFrame ke Elasticsearch index.

        Parameters:
        - dataframe: DataFrame yang akan di-ingest
        - index_name: nama index tujuan
        - id_field: kolom dari DataFrame yang digunakan sebagai _id (optional)
        """
        # Create index if it doesn't exist
        self.create_index_if_not_exists(index_name)
        actions = []
        for doc in data:
            action = {
                "_index": index_name,
                "_source": doc
            }
            if id_field and id_field in row:
                action["_id"] = str(doc[id_field])
            actions.append(action)

        success, _ = bulk(self.es, actions)
        print(f"✅ {success} dokumen berhasil di-ingest ke index `{index_name}`.")

    def to_pull(self, index_name: str, query: dict, size: int = 1000) -> pd.DataFrame:
        """
        Menarik data dari Elasticsearch berdasarkan query.

        Parameters:
        - index_name: nama index
        - query: dict Elasticsearch query DSL (misalnya {"match_all": {}})
        - size: jumlah maksimum dokumen yang ditarik

        Returns:
        - DataFrame hasil query
        """
        # Create index if it doesn't exist
        self.create_index_if_not_exists(index_name)
        
        response = self.es.search(index=index_name, query=query, size=size)
        hits = response.get("hits", {}).get("hits", [])
        data = [hit["_source"] for hit in hits]
        
        print(f"📥 Berhasil menarik {len(data)} dokumen dari index `{index_name}`.")
        return pd.DataFrame(data)

    def test_connection(self):
        return self.es.info()
    
def suggest_project_keywords(es_ingestor, input_projects):
    """Get or generate keywords for projects using Elasticsearch cache
    
    Args:
        es_ingestor: ElasticsearchIngestor instance
        input_projects: List of Project objects with name, id, and owner_id attributes
    
    Returns:
        List of dicts containing project info and keywords
    """
    try:
        # Query ES for existing keywords
        query = {
            "terms": {
                "project_name.keyword": [i.name for i in input_projects]
            }
        }

        result_df = es_ingestor.to_pull(index_name="project_keywords", query=query)
        if result_df.empty:
            result_df = pd.DataFrame(columns=['project_name'])

        final_result = []
        for doc in input_projects:
            project_name = doc.name
            owner_id = doc.owner_id
            project_id = doc.id

            if project_name in result_df['project_name'].to_list():
                # Get existing keywords from ES
                relevan_keyword = result_df[result_df['project_name']==project_name]['keywords'].values[0]
                print(f"Found cached keywords for project: {project_name}")
            else:
                # Generate new keywords
                print(f"Generating new keywords for project: {project_name}")
                relevan_keyword = generate_keywords_from_gemini(project_name)
                
                # Store in ES
                created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                data_ingest = {
                    "project_name": project_name,
                    "keywords": relevan_keyword,
                    "created_at": created_at
                }
                es_ingestor.to_ingest([data_ingest], index_name="project_keywords")

            final_result.append({
                'project_name': project_name,
                'relevan_keyword': relevan_keyword,
                "owner_id": owner_id,
                "project_id": project_id,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        return final_result
    except Exception as e:
        print(f"Error in suggest_project_keywords: {str(e)}")
        raise

def get_relevan_keyword(input_projects):
    """Main function to process projects and get/generate relevant keywords
    
    Args:
        input_projects: List of Project objects
    
    Returns:
        Dict with status and processed data
    """
    print(   os.getenv("ES_HOST", "localhost"),
        os.getenv("ES_PORT", 9200),
        os.getenv("ES_USERNAME"),
        os.getenv("ES_PASSWORD"))
    # Initialize ES connection
    es_ingestor = ElasticsearchIngestor(
        host=os.getenv("ES_HOST", "localhost"),
        port=os.getenv("ES_PORT", 9200),
        username=os.getenv("ES_USERNAME"),
        password=os.getenv("ES_PASSWORD")
    )

    # Get/generate keywords
    result = suggest_project_keywords(es_ingestor, input_projects)
    
    # Process results
    data_ingest = pd.DataFrame(result).explode('relevan_keyword')

    # Store in MySQL
    mysql = About_MySQL(
        db_host=os.getenv("DB_HOST"),
        db_port=os.getenv("DB_PORT"),
        db_user=os.getenv("DB_USER"),
        db_password=os.getenv("DB_PASSWORD"),
        db_name=os.getenv("DB_NAME")
    )
    mysql.to_push_data(data_ingest, 'keyword_projects', 'append')

    return {
        "status": "success",
        "data": data_ingest.to_dict(orient='records')
    }
