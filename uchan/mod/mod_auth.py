from flask import request, redirect, url_for, render_template, abort, flash, session

from uchan import g
from uchan.lib import ArgumentError, BadRequestError
from uchan.lib.mod_log import mod_log
from uchan.lib.moderator_request import get_authed, unset_mod_authed, set_mod_authed, get_authed_moderator
from uchan.mod import mod
from uchan.view import check_csrf_token, check_csrf_referer


@mod.before_request
def mod_restrict():
    if (request.endpoint != 'mod.mod_auth' and request.endpoint != 'mod.mod_reg') and not get_authed():
        return mod_abort_redirect()


def mod_abort_redirect():
    return redirect(url_for('.mod_auth'))


@mod.route('/')
def mod_index():
    return redirect(url_for('.mod_auth'))


@mod.route('/auth', methods=['GET', 'POST'])
def mod_auth():
    if request.method == 'POST':
        if get_authed():
            if request.form.get('deauth') == 'yes':
                if not check_csrf_token(request.form.get('token')):
                    abort(400)

                mod_log('logged out')
                unset_mod_authed()
                session.clear()

                return redirect(url_for('.mod_auth'))
        else:
            if not check_csrf_referer(request):
                raise BadRequestError('Bad referer header')

            username = request.form['username']
            password = request.form['password']

            mod_service = g.moderator_service

            if not mod_service.check_username_validity(username) or not mod_service.check_password_validity(password):
                raise BadRequestError('Invalid username or password')
            else:
                moderator = mod_service.find_moderator_username(username)
                if not moderator:
                    mod_log('log in with invalid username')
                    raise BadRequestError('Invalid username or password')
                else:
                    try:
                        mod_service.check_password(moderator, password)
                        set_mod_authed(moderator)
                        flash('Logged in')
                        mod_log('logged in')
                    except ArgumentError:
                        mod_log('log in with invalid password for username {}'.format(moderator.username))
                        raise BadRequestError('Invalid username or password')

        return redirect(url_for('.mod_auth'))
    else:
        authed = get_authed()
        moderator = get_authed_moderator() if authed else None
        return render_template('auth.html', authed=authed, moderator=moderator)


@mod.route('/auth/reg', methods=['POST'])
def mod_reg():
    if not check_csrf_referer(request):
        raise BadRequestError('Bad referer header')

    username = request.form['username']
    password = request.form['password']
    password_repeat = request.form['password_repeat']

    mod_service = g.moderator_service

    try:
        moderator = mod_service.user_register(username, password, password_repeat)
        set_mod_authed(moderator)
    except ArgumentError as e:
        raise BadRequestError(e.message)

    return redirect(url_for('.mod_auth'))
