from huggingface_hub import hf_hub_download


def download_data():
    return hf_hub_download(
        repo_id="Team-ACE/ToolACE",
        repo_type="dataset",
        filename="data.json",
        revision="6bda777c88d21e5a204703c1ee45597a8fa4f734",
        local_dir="data/raw",
    )

if __name__ == "__main__":
    print(download_data())
