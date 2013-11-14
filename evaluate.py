#!/usr/bin/python3
import os
import os.path
import sys
from subprocess import Popen, PIPE
from argparse import ArgumentParser
import utils
from myconfig import MyConfig


#Please `make -f Makefile.data prepare` first

config = MyConfig()

#change cwd to the libpinyin data directory
libpinyin_dir = config.getEvalsDir()
libpinyin_sub_dir = os.path.join(libpinyin_dir, 'data')
os.chdir(libpinyin_sub_dir)
#chdir done

datafiles = [config.getFinalModelFileName(), \
             config.getEvalsTextFileName(), \
             'deleted_bigram.db']


def checkData():
    #check data files
    for onefile in datafiles:
        if not os.access(onefile, os.F_OK):
            sys.exit('missing one data file:' + onefile)


def cleanUpData():
    #begin processing
    cmdline = ['/usr/bin/make', 'clean']
    subprocess = Popen(cmdline, shell=False, close_fds=True)
    (pid, status) = os.waitpid(subprocess.pid, 0)
    if status != 0:
        sys.exit('make clean for data files failed.')
    #end processing


def buildData():
    #begin processing
    cmdline = ['/usr/bin/make']
    subprocess = Popen(cmdline, shell=False, close_fds=True)
    (pid, status) = os.waitpid(subprocess.pid, 0)
    if status != 0:
        sys.exit('make build for data files failed.')
    #end processing


def estimateModel(reportfile):

    result_line_prefix = "average lambda:"
    avg_lambda = 0.

    #begin processing
    cmdline = ['../utils/training/estimate_interpolation']

    subprocess = Popen(cmdline, shell=False, stdout=PIPE, \
                           close_fds=True)

    reporthandle = open(reportfile, 'wb')

    for line in subprocess.stdout.readlines():
        reporthandle.writelines([line])
        #remove trailing '\n'
        line = line.decode('utf-8')
        line = line.rstrip(os.linesep)
        if line.startswith(result_line_prefix):
            avg_lambda = float(line[len(result_line_prefix):])

    reporthandle.close()

    (pid, status) = os.waitpid(subprocess.pid, 0)
    if status != 0:
        sys.exit('estimate interpolation model returns error.')
    #end processing

    return avg_lambda


def modifyLambda(lambdaparam):
    #begin processing
    cmdline = ['/usr/bin/make', 'modify', \
                   'LAMBDA_PARAMETER=' + str(lambdaparam)]
    subprocess = Popen(cmdline, shell=False, close_fds=True)
    (pid, status) = os.waitpid(subprocess.pid, 0)
    if status != 0:
        sys.exit('make rebuild for data files failed.')
    #end processing


def evaluateModel(reportfile):

    result_line_prefix = "correction rate:"
    rate = 0.

    #begin processing
    cmdline = '../utils/training/eval_correction_rate 2>"' + reportfile + '"'

    subprocess = Popen(cmdline, shell=True, stdout=PIPE, \
                           close_fds=True)

    for line in subprocess.stdout.readlines():
        #remove training '\n'
        line = line.decode('utf-8')
        line = line.rstrip(os.linesep)
        if line.startswith(result_line_prefix):
            rate = float(line[len(result_line_prefix):])

    os.waitpid(subprocess.pid, 0)
    #end processing

    return rate

if __name__ == '__main__':
    parser = ArgumentParser(description='Evaluate correction rate.')
    parser.add_argument('--finaldir', action='store', \
                            help='final directory', \
                            default=config.getFinalModelDir())
    parser.add_argument('tryname', action='store', \
                            help='the storage directory')

    args = parser.parse_args()
    print(args)
    tryname = 'try' + args.tryname

    trydir = os.path.join(args.finaldir, tryname)
    if not os.access(trydir, os.F_OK):
        sys.exit(tryname + "doesn't exist.")

    cwdstatuspath = os.path.join(trydir, config.getFinalStatusFileName())
    cwdstatus = utils.load_status(cwdstatuspath)
    if not utils.check_epoch(cwdstatus, 'Prune'):
        raise utils.EpochError('Please tryprune first.')

    if utils.check_epoch(cwdstatus, 'Evaluate'):
        sys.exit('already evaluated.')

    print('checking')
    checkData()

    modelfile = os.path.join(trydir, config.getFinalModelFileName())
    destfile = os.path.join(libpinyin_dir, 'data', \
                                config.getFinalModelFileName())

    utils.copyfile(modelfile, destfile)

    print('cleaning')
    cleanUpData()

    print('building')
    buildData()

    print('estimating')
    reportfile = os.path.join(trydir, 'estimate' + config.getReportPostfix())
    avg_lambda = estimateModel(reportfile)
    print('average lambda:', avg_lambda)

    cwdstatus['EvaluateAverageLambda'] = avg_lambda
    utils.store_status(cwdstatuspath, cwdstatus)

    print('modifying lambda')
    modifyLambda(avg_lambda)

    print('evaluating')
    reportfile = os.path.join(trydir, 'evaluate' + config.getReportPostfix())
    rate = evaluateModel(reportfile)
    print(tryname + "'s correction rate:", rate)

    cwdstatus['EvaluateCorrectionRate'] = rate
    utils.store_status(cwdstatuspath, cwdstatus)

    utils.sign_epoch(cwdstatus, 'Evaluate')
    utils.store_status(cwdstatuspath, cwdstatus)
    print('done')
