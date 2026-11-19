# Chinese Vocabulary Web App – V2

## Deploy on Streamlit Community Cloud

- Repository: your GitHub repository
- Branch: `main`
- Main file path: `app.py`

## Secrets

In Streamlit Cloud, open **Manage app → Settings → Secrets** and add:

```toml
APP_PASSWORD = "choose-a-private-password"
```

Do not commit the password to GitHub.

## Files

- `app.py`: application
- `requirements.txt`: Python dependencies
- `data/vocabulary.csv`: sample vocabulary dataset

## Important

This is a prototype containing 20 sample words only, not a complete verified HSK vocabulary database.
Favorites and settings are held in the current Streamlit session in this prototype. A persistent database can be added in a later version.
