#!/bin/bash

set -u

bold=$(tput bold)
normal=$(tput sgr0)


function help () {
    if [[ $# -gt 1 ]]; then
        CMD="print_${2}_help"
        $CMD
    else
        print_help
    fi
}


function print_help () {
    cat <<- EOF 
		
		${bold}NAME${normal}
		    ${bold}controller-admin.sh${normal} - Confine server administration script
		
		${bold}OPTIONS${normal}
		    ${bold}install_requirements${normal}
		        Installs all the controller requirements using apt-get and pip
		    
		    ${bold}clone${normal}
		        Creates a new Confine-Controller instance
		    
		    ${bold}help${normal}
		        Displays this help text or related help page as argument
		        for example:
		            ${bold}controller-admin.sh help clone${normal}
		
		EOF
}
# in


show () {
    echo " ${bold}\$ ${@}${normal}"
}
export -f show


run () {
    show ${@}
    ${@}
}
export -f run


check_root () {
    [ $(whoami) != 'root' ] && { echo -e "\nErr. This should be run as root\n" >&2; exit 1; }
}
export -f check_root


get_controller_dir () {
    if ! $(echo "import controller"|python 2> /dev/null); then
        echo -e "\nErr. Controller not installed.\n" >&2
        exit 1
    fi
    PATH=$(echo "import controller, os; print os.path.dirname(os.path.realpath(controller.__file__))" | python)
    echo $PATH
}
export -f get_controller_dir


function print_install_requirements_help () {
    cat <<- EOF 
		
		${bold}NAME${normal}
		    ${bold}controller-admin.sh install_requirements${normal} - Installs all the controller requirements using apt-get and pip
		
		${bold}OPTIONS${normal}
		    ${bold}-m, --minimal${normal}
		        Installs all the controller requirements using apt-get and pip
		    
		    ${bold}-h, --help${normal}
		        Displays this help text
		
		EOF
}


function install_requirements () {
    opts=$(getopt -o mh -l minimal,help -- "$@") || exit 1
    set -- $opts
    minimal=false
    
    while [ $# -gt 0 ]; do
        case $1 in
            -m|--minimal) minimal=true; shift ;;
            -h|--help) print_deploy_help; exit 0 ;;
            (--) shift; break;;
            (-*) echo "$0: Err. - unrecognized option $1" 1>&2; exit 1;;
            (*) break;;
        esac
        shift
    done
    unset OPTIND
    unset opt
    
    check_root
    CONTROLLER_PATH=$(get_controller_dir)
    
    MINIMAL_APT="python-pip python-m2crypto python-psycopg2 postgresql rabbitmq-server"
    EXTENDED_APT="libapache2-mod-wsgi git mercurial fuseext2 screen openssh-server tinc"
    
    run apt-get update
    run apt-get install -y "$MINIMAL_APT"
    if ! $minimal; then
        run apt-get install -y "$EXTENDED_APT"
    
        # Some versions of rabbitmq-server will not start automatically by default unless ...
        sed -i "s/# Default-Start:.*/# Default-Start:     2 3 4 5/" /etc/init.d/rabbitmq-server
        sed -i "s/# Default-Stop:.*/# Default-Stop:      0 1 6/" /etc/init.d/rabbitmq-server
        run update-rc.d rabbitmq-server defaults
    fi
    run pip install -r http://redmine.confine-project.eu/projects/controller/repository/revisions/master/raw/requirements.txt
}
export -f install_requirements


print_clone_help () {
    cat <<- EOF 
		
		${bold}NAME${normal}
		    ${bold}controller-admin.sh clone${normal} - Create a new Confine-Controller instance
		
		${bold}SYNOPSIS${normal}
		    Options: [ -s SKELETONE ]
		    
		${bold}OPTIONS${normal}
		    ${bold}-s, --skeletone${normal}
		            default confine
		    
		    ${bold}-h, --help${normal}
		            This help message
		    
		${bold}EXAMPLES${normal}
		    controller-admin.sh clone communitylab --skeletone communitylab
		    
		    controller-admin.sh clone communitylab
		
		EOF
}


function clone () {
    local SKELETONE=""
    local PROJECT_NAME="$2"; shift
    
    opts=$(getopt -o s:h -l skeletone:,help -- "$@") || exit 1
    set -- $opts
    minimal=false
    
    set -- $opts
    while [ $# -gt 0 ]; do
        case $1 in
            -s|--skeletone) local SKELETONE="${2:1:${#2}-2}"; shift ;;
            -h|--help) print_clone_help; exit 0 ;;
            (--) shift; break;;
            (-*) echo "$0: Err. - unrecognized option $1" 1>&2; exit 1;;
            (*) break;;
        esac
        shift
    done
    unset OPTIND
    unset opt
    [ $(whoami) == 'root' ] && { echo -e "\nYou don't want to run this as root\n" >&2; exit 1; }
    
    CONTROLLER_PATH=$(get_controller_dir)
    run django-admin.py startproject $PROJECT_NAME --template="${CONTROLLER_PATH}/conf/project_template"
    # TODO skeletone
    # [ $SKELETONE ] && run cp -r "${CONTROLLER_PATH}/projects/${SKELETONE}/*" $PROJECT_NAME/$PROJECT_NAME
    # This is a workaround for this issue https://github.com/pypa/pip/issues/317
    run chmod +x $PROJECT_NAME/manage.py
}
export -f clone


[ $# -lt 1 ] && print_help
$1 "${@}"