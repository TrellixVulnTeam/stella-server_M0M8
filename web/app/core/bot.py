import re
import os
import random

from github import Github
from datetime import datetime

from ..util import make_tarfile

from ..models import System
import ruamel.yaml


class Bot:
    def validate(self, ranking_str, k=None):
        def _construct_error_string(error_log):
            message = []
            error_count = sum([len(error_log[s]) for s in error_log])
            message.append('There are {} errors in your file:\n'.format(str(error_count)))
            for error_type in error_log:
                if len(error_log[error_type]) > 1:
                    message.append(
                        error_log[error_type][0] + ' and {} more lines.\n'.format(str(len(error_log[error_type]) - 1)))
                else:
                    message.append(error_log[error_type][0] + '\n')
            return message

        error_log = {}
        run_tag = {}
        topics = {}
        samples = []
        if ranking_str:
            ranking_str_decodet = ranking_str.read().decode("utf-8")
            lines = ranking_str_decodet.split('\n')[:-1]
            if k:
                for _ in range(0, k):
                    s = lines[random.randint(0, len(lines) - 1)]
                    samples.append(s)
            else:
                samples = lines

            for line in samples:
                if '\t' in line:
                    fields = line.split('\t')
                elif ' ' in line:
                    fields = line.split(' ')
                else:
                    error_log.setdefault('wrong delimeter', []).append(
                        'Error line {} - Could not detect delimeter'.format(str(lines.index(line) + 1)))
                    continue

                if len(fields) != 6:
                    error_log.setdefault('missing fields', []).append(
                        'Error line {} - Missing fields'.format(str(lines.index(line) + 1)))
                    continue

                run_tag.setdefault('run_tag', fields[5])
                if not re.search("^[A-Za-z0-9_.-]{1,24}$", fields[5]):
                    error_log.setdefault('malformed run tag', []).append(
                        'Error line {} - Run tag {} is malformed'.format(str(lines.index(line) + 1),
                                                                         str(fields[5])))
                    continue
                else:
                    if not fields[5] == run_tag['run_tag']:
                        error_log.setdefault('inconsistent run tag', []).append(
                            'Error line {} - Run tag is inconsistent ({} and {})'.format(
                                str(lines.index(line) + 1),
                                str(fields[5]), str(run_tag['run_tag'])))
                        continue
                # todo: Topic anzahl abgleichen

                if 'Q0'.casefold() not in fields[1].casefold():
                    error_log.setdefault('Q0', []).append('Error line {} - "Field 2 is {} not "Q0"'.format(
                        str(lines.index(line) + 1), str(fields[1])))
                    continue

                if not fields[3].isdigit():
                    error_log.setdefault('rank', []).append(
                        'Error line {} - "Column 4 (rank) {} must be an integer"'.format(
                            str(lines.index(line) + 1), str(fields[3])))
                    continue

                # if not re.search("^[A-Za-z0-9-]{1,24}$", fields[2]):
                # error = 'Error line {} - "Invalid docid {}"\n'.format(str(lines.index(line) + 1),
                # str(fields[2]))
                # error_log.setdefault('docid', []).append(error)
                # continue
                # if(error_log):
                #     print(error_log)
            if len(error_log) == 0:
                return False
        else:
            return 'Runfile is empty!'
        return _construct_error_string(error_log)

    def compressFile(self, subdir):

        input = os.path.join(subdir, 'run.txt')
        output = os.path.join(subdir, 'run.tar.gz')
        make_tarfile(output, input)
        return output

    def saveFile(self, file, filename):
        if not os.path.exists('uploads'):
            os.makedirs('uploads')

        subdir = os.path.join('uploads', filename)
        if not os.path.exists(subdir):
            os.makedirs(subdir)

        run_path = os.path.join(subdir, 'run.txt')

        file.save(run_path)

        return subdir


    def saveSplits(self, TRECstr, filename):
        files = {}
        lines = TRECstr.split('\n')[:-1]
        for line in lines:
            if '\t' in line:
                fields = line.split('\t')
            elif ' ' in line:
                fields = line.split(' ')
            else:
                print('Error Line {} - Could not detect delimeter.\n'.format(str(lines.index(line) + 1)))

            files.setdefault(fields[0], []).append(line)
        if not os.path.exists(os.path.join('uploads', str(filename.split('.')[0]))):
            os.makedirs(os.path.join('uploads', str(filename.split('.')[0])))
        for file in files:
            with open(os.path.join('uploads', str(filename.split('.')[0]),
                                   str(filename.split('.')[0]) + '_' + file + '.txt'), 'w') as outfile:
                for line in files[file]:
                    outfile.write(line + '\n')
        return files

    @staticmethod
    def push_to_github(token, repo_name):
        g = Github(token)
        repo = g.get_user().get_repo(repo_name)

        file = repo.get_contents('README.md')
        readme_content = file.decoded_content.decode('utf-8')

        commit_message = 'update at ' + str(datetime.now())
        updated_readme_content = readme_content + '  \n' + str(datetime.now())
        repo.update_file('README.md', commit_message, updated_readme_content, file.sha)

    @staticmethod
    def create_repo(token, repo_name, orga='stella-project'):
        g = Github(token)
        stella_project = g.get_organization(orga)
        stella_project.create_repo(repo_name, private=True)

    @staticmethod
    def create_precom_repo(token, repo_name, run_tar_in, type):
        g = Github(token)
        orga_name = 'stella-project'
        stella_project = g.get_organization(orga_name)
        template = stella_project.get_repo('stella-micro-template-precom')
        repo = stella_project.create_repo(repo_name + '_precom', private=True)

        for file in template.get_contents('.'):
            filename = file.name
            if filename not in ['test', 'precom']:
                commit_msg = 'add ' + filename
                repo.create_file(filename, commit_msg, file.decoded_content.decode('utf-8'))

        for test_file in template.get_contents('test'):
            filename = test_file.name
            commit_msg = 'add ' + filename
            repo.create_file('test/'+filename, commit_msg, test_file.decoded_content.decode('utf-8'))

        repo.create_file('precom/rank/.gitkeep', 'add rank dir', " ")
        repo.create_file('precom/rec/datasets/.gitkeep', 'add rec data dir', " ")
        repo.create_file('precom/rec/publications/.gitkeep', 'add rec pub dir', " ")

        if type == 'RANK':
            run_tar_path = 'precom/rank/run.tar.gz'
        if type == 'REC':
            run_tar_path = 'precom/rec/datasets/run.tar.gz'
        with open(run_tar_in, 'rb') as run_in:
            repo.create_file(run_tar_path, 'add run.tar.gz', run_in.read())

        return repo.html_url

    @staticmethod
    def update_stella_app(type='all', token=None):

        yml_path = 'uploads/docker-compose.yml'

        if type == 'all':
            systems = System.query.filter_by(status='running').all()
            repo_name = 'stella-app'
        if type == 'rec':
            systems = System.query.filter_by(type='REC', status='running').all()
            repo_name = 'stella-app'
        if type == 'rank':
            systems = System.query.filter_by(type='RANK', status='running').all()
            repo_name = 'stella-app'

        compose = {'version': '3',
                   'networks': {'stella-shared': {'external': {'name': 'stella-server_default'}}},
                   'services': {
                       'app': {
                           'build': './app',
                           'volumes': ['/var/run/docker.sock/:/var/run/docker.sock', './app/log:/app/log'],
                           'ports': ["8080:8000"],
                           'depends_on': [system.name for system in systems],
                           'networks': ['stella-shared']
                     }
                    }
                   }

        if type == 'all':
            ranksys = System.query.filter_by(type='REC', status='running').all()
            recsys = System.query.filter_by(type='REC', status='running').all()

            if ranksys and recsys:
                compose['services']['app']['environment'] = ['RANKSYS_LIST=' + ' '.join([sys.name for sys in ranksys]),
                                                             'RECSYS_LIST=' + ' '.join([sys.name for sys in recsys]),
                                                             'RANKSYS_BASE=rank_dummy',
                                                             'RECSYS_BASE=gesis_rec_micro']

            if not ranksys and recsys:
                compose['services']['app']['environment'] = ['RECSYS_LIST=' + ' '.join([sys.name for sys in recsys]),
                                                             'RECSYS_BASE=gesis_rec_micro']

            if ranksys and not recsys:
                compose['services']['app']['environment'] = ['RANKSYS_LIST=' + ' '.join([sys.name for sys in ranksys]),
                                                             'RANKSYS_BASE=rank_dummy']

        if type == 'rank':
            ranksys = System.query.filter_by(type='REC', status='running').all()
            if ranksys:
                compose['services']['app']['environment'] = ['RANKSYS_LIST=' + ' '.join([sys.name for sys in ranksys]),
                                                             'RANKSYS_BASE=rank_dummy']

        if type == 'rec':
            recsys = System.query.filter_by(type='REC', status='running').all()
            if recsys:
                compose['services']['app']['environment'] = ['RECSYS_LIST=' + ' '.join([sys.name for sys in recsys]),
                                                             'RECSYS_BASE=gesis_rec_micro']


        for system in systems:
            compose['services'][str(system.name)] = {
                'build': system.url,
                'container_name': system.name,
                'volumes': ['./data/:/data/'],
                'networks': ['stella-shared']
            }

        yaml = ruamel.yaml.YAML()
        yaml.indent(sequence=4, offset=4)

        with open(yml_path, 'w') as file:
            yaml.dump(compose, file)

        with open(yml_path) as yml_in:
            updated_content = yml_in.read()
            print(updated_content)

        if token:
            g = Github(token)
            orga_name = 'stella-project'
            stella_project = g.get_organization(orga_name)
            stella_app = stella_project.get_repo(repo_name)

            file = stella_app.get_contents('docker-compose.yml')

            commit_message = 'automatic update'

            with open(yml_path) as yml_in:
                updated_content = yml_in.read()

            stella_app.update_file('docker-compose.yml', commit_message, updated_content, file.sha)
