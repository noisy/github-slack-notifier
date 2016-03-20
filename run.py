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
        'user': lambda e: '<https://github.com/{user}|{user}>'.format(
            user=e.actor.login
        ),
        'branch': lambda e: '<https://github.com/{repo}/tree/{branch}|{branch}>'.format(
            repo=e.repo.full_name,
            branch=e.payload['ref'].split('/')[-1]
        ),
        'repo': lambda e: '<https://github.com/{repo}|{repo}>'.format(
            repo=e.repo.full_name
        ),
        'pr_number': lambda e: '<https://github.com/{repo}/pull/{pr_number}|{repo}#{pr_number}>'.format(
            repo=e.repo.full_name,
            pr_number=event.payload['number']
        ),
        'issue_number': lambda e: '<https://github.com/{repo}/issues/{issue_number}|{repo}#{issue_number}>'.format(
            repo=e.repo.full_name,
            issue_number=event.payload['issue']['number']
        ),
        'commits': lambda e: '\n'.join(
            [
                '<https://github.com/{repo}/commit/{sha}|{sha_short}> {message}'.format(
                    repo=e.repo.full_name,
                    sha=commit['sha'],
                    sha_short=commit['sha'][:8],
                    message=commit['message']
                )
                for commit in event.payload['commits']
            ]
        ),
        'fork_repo': lambda e: '<https://github.com/{fork_repo}|{fork_repo}>'.format(
            fork_repo=e.payload['forkee']['full_name']
        ),
        'comment': lambda e: event.payload['comment']['body'],
        'release': lambda e: '<{release_url}|{repo}#{release_name}>'.format(
            release_url=event.payload['release']['html_url'],
            repo=e.repo.full_name,
            release_name=event.payload['release']['html_name'],
        ),
        'release_description': lambda e: event.payload['release']['body'],

    }

    return link_dict.get(string)(event)


def describe_event(event):
    msg = ''
    attachments = ''
    if event.type == 'PullRequestEvent':
        if event.payload['action'] == 'opened':
            msg = '{user} opened pull request {pr_number}'
        elif event.payload['action'] == 'closed':
            msg = '{user} closed pull request {pr_number}'
        else:
            pass

    elif event.type == 'PushEvent':
        msg = '{user} pushed to {branch} at {repo}'
        attachments = '{commits}'
    elif event.type == 'IssuesEvent':
        if event.payload['action'] == 'opened':
            msg = '{user} opened issue {issue_number}'
        else:
            pass
    elif event.type == 'ForkEvent':
        msg = '{user} forked {repo} to {fork_repo}'
    elif event.type == 'WatchEvent':
        msg = '{user} starred {repo}'
    elif event.type == 'IssueCommentEvent':
        msg = '{user} commented on issue {issue_number}'
        attachments = '{comment}'
    elif event.type == 'CreateEvent':  # fork of repository
        if event.payload['ref_type'] == 'branch':
            msg = '{user} created branch {branch} at {repo}'
    elif event.type == 'ReleaseEvent':
        msg = '{} created a release of {repo} at {release}'
        attachments = '{release_description}'
    elif event.type == 'DeleteEvent':
        # Represents a deleted branch or tag.
        # Note: webhooks will not receive this event for
        # if more than three tags are deleted at once.
        pass
    elif event.type == 'PullRequestReviewCommentEvent':
        pass
    elif event.type == 'CommitCommentEvent':
        pass

    return format_str(msg, event), format_str(attachments, event)


def main():
    already_displayed = []

    while True:
        for repo_name in REPOSITORIES:
            events = g.get_repo(repo_name).get_network_events()
            for event in events[:10]:
                if event.created_at + timedelta(minutes=10) > datetime.now():

                    msg, attachments = describe_event(event)

                    if event.id not in already_displayed and msg:
                        already_displayed.append(event.id)
                        slack.chat.post_message(
                            SLACK_CHANNEL,
                            msg,
                            as_user=True,
                            unfurl_links=False,
                            attachments=('[{"text": "%s"}]' % attachments) if attachments else None
                        )

        sleep(60)


if __name__ == "__main__":
    main()
