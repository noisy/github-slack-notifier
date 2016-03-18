import os
import re
from time import sleep
from datetime import datetime, timedelta
from github import Github
from slacker import Slacker

slack = Slacker(os.environ.get('SLACK_TOKEN'))
g = Github(os.environ.get('GITHUB_LOGIN'), os.environ.get('GITHUB_PASS'))

REPOSITORIES = [
    'cryptonomex/graphene-ui',
    'cryptonomex/graphene',
    'bitshares/bitshares-2-ui',
    'bitshares/bitshares-2',
]
SLACK_CHANNEL = '#bottest'


def format_str(string, event):
    matches = re.findall('{(.*?)}', string)
    kwargs = {match: add_links(match, event) for match in matches}
    return string.format(**kwargs)


def add_links(string, event):
    link_dict = {
        'user': lambda e: '<https://github.com/{user}|{user}>'.format(user=e.actor.login),
        'branch': lambda e: '<https://github.com/{repo}/tree/{branch}|{branch}>'.format(
            repo=e.repo.full_name, branch=e.payload['ref'].split('/')[-1]
        ),
        'repo': lambda e: '<https://github.com/{repo}|{repo}>'.format(repo=e.repo.full_name),
        'pr_number': lambda e: '<https://github.com/{repo}/pull/{pr_number}|{repo}#{pr_number}>'.format(
            repo=e.repo.full_name, pr_number=event.payload['number']
        ),
        'issue_number': lambda e: '<https://github.com/{repo}/issues/{issue_number}|{repo}#{issue_number}>'.format(
            repo=e.repo.full_name, issue_number=event.payload['issue']['number']
        ),
        'commits': lambda e: '\n'.join(
            [
                '    <https://github.com/{repo}/commit/{sha}|{sha_short}> {message}'.format(
                    repo=e.repo.full_name, sha=commit['sha'], sha_short=commit['sha'][:8], message=commit['message']
                )
                for commit in event.payload['commits']
            ]
        )

    }

    return link_dict.get(string)(event)


def describe_event(event):
    msg = ''
    if event.type == 'PullRequestEvent':
        if event.payload['action'] == 'opened':
            msg = '{user} opened pull request {repo}#{pr_number}'
        elif event.payload['action'] == 'closed':
            msg = '{user} closed pull request {repo}#{pr_number}'

    elif event.type == 'PushEvent':
        msg = '{user} pushed to {branch} at {repo}\n{commits}'

    elif event.type == 'IssuesEvent':
        if event.payload['action'] == 'opened':
            msg = '{user} opened issue {repo}#{issue_number}'
        else:
            pass

    # if event.type == 'CreateEvent': # fork of repository
    #     pass
    # elif event.type == 'ReleaseEvent':
    #     pass
    # elif event.type == 'PullRequestReviewCommentEvent':
    #     pass
    # elif event.type == 'ForkEvent':
    #     pass
    # elif event.type == 'DeleteEvent':
    #     pass
    # elif event.type == 'CommitCommentEvent':
    #     pass
    # elif event.type == 'WatchEvent':
    #     pass
    # elif event.type == 'IssueCommentEvent':
    #     pass

    return format_str(msg, event)


def main():
    already_displayed = []

    while True:
        for repo_name in REPOSITORIES:
            events = g.get_repo(repo_name).get_network_events()
            for event in events[:10]:
                if event.created_at + timedelta(days=4) > datetime.now():

                    msg = describe_event(event)

                    if event.id not in already_displayed and msg:
                        already_displayed.append(event.id)
                        slack.chat.post_message(
                            SLACK_CHANNEL, msg, as_user=True, unfurl_links=True
                        )

        sleep(60)


if __name__ == "__main__":
    main()
