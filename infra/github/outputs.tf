output "repository_url" {
  value = data.github_repository.this.html_url
}

output "streamlit_next_step" {
  value = "share.streamlit.io -> Create app -> ${data.github_repository.this.full_name} / develop (QA) e main (PROD) / app/streamlit_app.py"
}
