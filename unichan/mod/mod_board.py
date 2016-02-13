from flask import request, redirect, url_for, render_template, abort, flash

from unichan import g
from unichan.lib import roles, ArgumentError
from unichan.lib.models import Board
from unichan.mod import mod, mod_role_restrict
from unichan.view import check_csrf_token, with_token


@mod.route('/mod_board')
@mod_role_restrict(roles.ROLE_ADMIN)
def mod_boards():
    boards = g.board_service.get_all_boards()

    return render_template('mod_boards.html', boards=boards)


@mod.route('/mod_board/add', methods=['POST'])
@mod_role_restrict(roles.ROLE_ADMIN)
@with_token()
def mod_board_add():
    board_name = request.form['board_name']

    if not g.board_service.check_board_name_validity(board_name):
        flash('Invalid board name')
        return redirect(url_for('.mod_boards'))

    board = Board()
    board.name = board_name

    try:
        g.board_service.add_board(board)
        flash('Board added')
    except ArgumentError as e:
        flash(e.message)

    return redirect(url_for('.mod_board', board_name=board.name))


@mod.route('/mod_board/delete', methods=['POST'])
@mod_role_restrict(roles.ROLE_ADMIN)
@with_token()
def mod_board_delete():
    board_name = request.form['board_name']

    board = g.board_service.find_board(board_name)
    if not board:
        abort(404)

    g.board_service.delete_board(board)
    flash('Board deleted')

    return redirect(url_for('.mod_boards'))


@mod.route('/mod_board/<board_name>', methods=['GET', 'POST'])
@mod_role_restrict(roles.ROLE_ADMIN)
def mod_board(board_name):
    board = g.board_service.find_board(board_name)
    if not board:
        abort(404)

    board_config_row = board.config
    board_config = g.config_service.load_config(board_config_row)

    if request.method == 'GET':
        return render_template('mod_board.html', board=board, board_config=board_config)
    else:
        form = request.form

        if not check_csrf_token(form.get('token')):
            abort(400)

        try:
            g.config_service.save_from_form(board_config, board_config_row, form)
            flash('Board config updated')
            g.board_cache.invalidate_board_config(board_name)
        except ArgumentError as e:
            flash(str(e))

        return redirect(url_for('.mod_board', board_name=board_name))