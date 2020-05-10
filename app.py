from flask import Flask, render_template, request, abort
import nltk, json, os, re, warnings, operator, html, time

def _edit_dist_init(len1, len2):
    lev = []
    for i in range(len1):
        a = lev.append([0] * len2)  # initialize 2D array to zero
    for i in range(len1):
        b = lev[i][0] = i  # column 0: 0,1,2,3,4,...
    for j in range(len2):
        c = lev[0][j] = j  # row 0: 0,1,2,3,4,...
    return lev

def _edit_dist_step(lev, i, j, s1, s2, substitution_cost=1, transpositions=False):
    c1 = s1[i - 1]   #last alphabet of the string
    c2 = s2[j - 1]   #last alphabet of the string

    # skipping a character in s1
    a = lev[i - 1][j] + 1
    # skipping a character in s2
    b = lev[i][j - 1] + 1
    # substitution
    c = lev[i - 1][j - 1] + (substitution_cost if c1 != c2 else 0)  #replacement

    # transposition
    d = c + 1  # never picked by default
    if transpositions and i > 1 and j > 1:
        if s1[i - 2] == c2 and s2[j - 2] == c1:
            d = lev[i - 2][j - 2] + 1

    # pick the cheapest
    lev[i][j] = min(a, b, c, d)

    return lev[i][j]

def _edit_dist_backtrace(lev):
    i, j = len(lev) - 1, len(lev[0]) - 1
    counter = []
    alignment = [(i, j)]

    while (i, j) != (0, 0):
        old_i = i
        old_j = j
        directions = [
            (i - 1, j - 1),  # substitution (diagonal)
            (i - 1, j),  # skip s1 (above)
            (i, j - 1),  # skip s2 (left)

        ]

        direction_costs = (
            (lev[i][j] if (i >= 0 and j >= 0) else float("inf"), (i, j))
            for i, j in directions
        )

        X, (i, j) = min(direction_costs, key=operator.itemgetter(0))


        if X == lev[old_i][old_j] and lev[old_i-1][old_j-1]==lev[old_i][old_j]:
            counter.append('equal')
        elif X == lev[old_i-1][old_j-1]:
            counter.append('substitution')
        elif X == lev[old_i-1][old_j]:
            counter.append('deletion')
        elif X == lev[old_i][old_j-1]:
            counter.append('insertion')
        else:
            print('error')
            continue

        alignment.append((i, j))
    return list(reversed(alignment)), counter

def edit_distance_align(s1, s2, substitution_cost=1):

    # set up a 2-D array
    len1 = len(s1)
    len2 = len(s2)
    lev = _edit_dist_init(len1 + 1, len2 + 1)

    # iterate over the array
    for i in range(len1):
        for j in range(len2):
            _edit_dist_step(
                lev,
                i + 1,
                j + 1,
                s1,
                s2,
                substitution_cost=substitution_cost,
                transpositions=False,
            )

    # backtrace to find alignment
    alignment, counter = _edit_dist_backtrace(lev)
    return alignment, counter, lev[len1][len2]

# Prevent special characters like & and < to cause the browser to display something other than what you intended.
def html_escape(text):
    return html.escape(text)

def highlight_text(A,B):
    start_time = time.time()
    a = A.split(" ")
    b = B.split(" ")
    alignment, counter, edit_dist = edit_distance_align(a, b, substitution_cost=1)
    counter = list(reversed(counter))
    highlighted_text = []
    token_a, token_b, pointer_a, pointer_b = a, b, 0, 0
    inst, delete, subst = 0, 0, 0

    sub_html_1, sub_html_2, sub_html_3 = "<div class='sub'><s><p>", "</p></s><p class='sub'>", "</p></div>"


    for index, action in enumerate(counter): # counter will always take the longest string
        if action is "equal":
            highlighted_text.append("<div class='eq grid-item'><p>"+token_a[pointer_a]+"</p><p>&nbsp;</p></div>")
            pointer_a += 1
            pointer_b += 1

        elif action is "substitution":
            subst += 1
            sub_word = token_b[pointer_b]
            try:
                orig_word = token_a[pointer_a]
            except:
                abort(404)
            highlighted_text.append(sub_html_1+orig_word+sub_html_2+sub_word+sub_html_3)
            pointer_a += 1
            pointer_b += 1

        elif action is "deletion":
            delete += 1
            word = token_a[pointer_a]
            # highlight it red
            highlighted_text.append("<div class='del grid-item'><p class='del'>"+word+"</p><p>&nbsp;</p></div>")
            pointer_a += 1

        elif action is "insertion":
            inst += 1
            word = token_b[pointer_b]
            # originally yellow 235 219 52; now red
            highlighted_text.append('<div class="ins grid-item"><p>&nbsp;</p><p class="ins">' + word + '</p></div>')
            pointer_b += 1

    highlighted_text = ' '.join(highlighted_text)
    time_taken = time.time() - start_time
    return highlighted_text, counter, inst, delete, subst, edit_dist, len(a), round(time_taken,3)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# This page will be the page after the form
@app.route('/report')
def report():
    truth = request.args.get('truth')
    transcript = request.args.get('transcript')

    highlighted_text, counter,  insertion, deletion, substitution, edit_distance, orig_len, time_taken = highlight_text(truth, transcript)
    word_error = str(round(100*edit_distance/orig_len, 2))+'%'

    return render_template('report.html',highlighted_text=highlighted_text,
            insertion=insertion, deletion=deletion, substitution=substitution,
            word_error = word_error, time_taken = time_taken)

if __name__ == '__main__':
    app.run()
