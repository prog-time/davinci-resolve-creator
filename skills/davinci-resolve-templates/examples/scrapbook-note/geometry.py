"""Shared layout for Scrapbook Note (frame px, Y from top).

Measured on the 1094x638 reference screenshot; content bbox scaled x1.65 and
centered in 1920x1080 via P().
"""
S = 1.65


def P(x, y):
    return round(960 + (x - 549) * S, 1), round(540 + (y - 315) * S, 1)


def L(v):
    return round(v * S)


G = dict(
    # paper (screenshot box 195..880 x 105..530)
    paper_c=P(537.5, 317.5), paper_w=L(685), paper_h=L(425),
    hole_n=9, hole_x0=L(245 - 195), hole_step=L(65.6), hole_y=L(152 - 105), hole_d=L(27),
    line_n=10, line_y0=L(222 - 105), line_step=L(29.5),
    # polaroids
    pl_c=P(131.5, 192.5), pl_w=L(210), pl_h=L(245), pl_angle=4,
    pr_c=P(957.5, 382.5), pr_w=L(215), pr_h=L(235), pr_angle=-5,
    # clips
    clip_l_c=P(205, 107), clip_l_angle=-25,
    clip_r_c=P(881, 287), clip_r_angle=20,
    # tape
    tape_c=P(802, 115), tape_w=L(330), tape_h=L(95), tape_angle=-17,
    # sticky + pin + sticky text
    sticky_c=P(852, 522), sticky_w=L(215), sticky_h=L(170), sticky_angle=-4,
    pin_c=P(877, 462),
    sticky_text_c=P(850, 528),
    # title / underline / body
    title_left=P(260, 0)[0], title_cy=P(0, 252)[1],
    ul_c=P(533.5, 279), ul_w=L(545),
    body_left=P(283, 0)[0], body_top=P(0, 302)[1],
)
