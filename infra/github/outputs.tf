output "repository_url" {
  value = github_repository.this.html_url
}

output "clone_url" {
  value = github_repository.this.ssh_clone_url
}

output "streamlit_next_step" {
  value = "share.streamlit.io -> Create app -> ${github_repository.this.full_name} / main / app/streamlit_app.py"
}
