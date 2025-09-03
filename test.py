import git

# existing repo
repo = git.Repo('https://github.com/Unknown040/test_040test.git')

url = repo.remotes.origin.url
print(url)