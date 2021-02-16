

  it('creates an issue - $OWNER_USERNAME/$REPO_NAME $HEAD_COMMIT_SHA', async () => {
    event.payload = {
      "ref": "refs/heads/master",
      "after": "$HEAD_COMMIT_SHA",
      "head_commit": {
        "id": "$HEAD_COMMIT_SHA",
        "timestamp": "$DATE",
        "author": {
          "username": "$HEAD_COMMIT_AUTHOR_USERNAME"
        }
      },
      "repository": {
        "name": "$REPO_NAME",
        "owner": {
          "login": "$OWNER_USERNAME"
        },
        "master_branch": "master"
      }
    }

    github.repos.getCommit.mockReturnValue(Promise.resolve({
        data: fs.readFileSync('$DIFF_FILENAME', 'utf8'),
        headers: { 'content-length': 1 }
    }))
    await app.receive(event)

    for (issue of github.issues.create.mock.calls) {
        console.log(`$${new Date().toISOString()}: Output issue for $${issue[0].owner}/$${issue[0].repo}: $${truncate(issue[0].title, 40)}`)
        stringify([
            [issue[0].owner, issue[0].repo, event.payload.head_commit.timestamp, issue[0].title, issue[0].body]
          ], function(err, output){
            if (err) {
              console.error(err)
              return
            }
            stream.write(output)
          })
    }
  })
