

## Running without Docker

To run the application without Docker, follow these steps:

1.  **Setup Environment Variables:**
    Ensure you have configured your `.env` file as described in the "Setup Environment Variables" section above. These variables will be used by the Python scripts.

2.  **Pull Milvus and Temporal Images:**
    Ensure you have Milvus and Temporal services running locally. You can pull their Docker images and run them manually if you prefer not to use `docker-compose`.
    
    For Milvus:
    ```bash
    docker pull milvusdb/milvus:v2.5.5
    docker run -d --name milvus_standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:v2.5.5
    ```
    
    For Temporal (auto-setup for development):
    ```bash
    docker pull temporalio/auto-setup:1.27.2
    docker run -d --name temporal_server -p 7233:7233 temporalio/auto-setup:1.27.2
    ```

2.  **Set up Virtual Environment:**
    Navigate to the project root directory and create a virtual environment.
    ```bash
    python -m venv .venv
    ```

3.  **Activate Virtual Environment:**
    Activate the virtual environment. On Windows, use:
    ```bash
    .venv\Scripts\activate
    ```
    On macOS/Linux, use:
    ```bash
    source .venv/bin/activate
    ```

4.  **Install Dependencies:**
    Install the required Python packages.
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the Temporal Worker:**
    In a separate terminal, with the virtual environment activated, start the Temporal worker.
    ```bash
    python worker.py
    ```

6.  **Run the Main Workflow:**
    In another terminal, with the virtual environment activated, run the main script to start the workflow.
    ```bash
    python main.py
    ```

## Running with Docker using Docker Compose

To run the application using Docker Compose, follow these steps:

1.  **Setup Environment Variables:**
    Ensure you have configured your `.env` file as described in the "Setup Environment Variables" section above. Docker Compose will automatically pick up variables from this file.

2.  **Ensure Docker is Running:**
    Make sure Docker Desktop (or your Docker environment) is running on your system.

3.  **Navigate to Project Root:**
    Open your terminal or command prompt and navigate to the root directory of this project where the `docker-compose.yml` file is located.

4.  **Start Services:**
    Run the following command to build and start all services defined in `docker-compose.yml` in detached mode:
    ```bash
    docker-compose up --build -d
    ```
    This command will:
    -   Build the `worker` service Docker image based on the `Dockerfile`.
    -   Pull the `milvusdb/milvus` and `temporalio/auto-setup` images if not already present.
    -   Start the `milvus`, `temporal`, `temporal-ui`, and `worker` services.

5.  **Verify Services (Optional):**
    You can check the status of your running Docker containers with:
    ```bash
    docker-compose ps
    ```

6.  **Access Temporal Web UI (Optional):**
    If the `temporal-ui` service is running, you can access the Temporal Web UI by navigating to `http://localhost:8080` in your web browser.

7.  **Stop Services:**
    To stop and remove the containers, networks, and volumes created by `docker-compose up`, run:
    ```bash
    docker-compose down
    ```

**Note:** Currently, the milvus does not work with docker-compose for this worker. So without docker compose, the milvus has to be run manually.



**Design Explanation:**

1. Created a Temporal workflow using sandboxed as false to allow network operations and certain import.
2. Created Activities to perform the following operations:
    -   Download the file from the given URL.
    -   Extract the file.
    -   Read the file and convert it to a list of Elements.
    -   Insert data into the Milvus collection.
3. Stored the List of Elements in global Variable as temporal doesnt support serialization of complex values/class.(Alternative: Could also store on DB for better processing and avoid memory leaks)
4. Used Async io library to perform the operations like creating embeddings and inserting data into Milvus.(Used asyncio.create_task, asyncio.gather) 
