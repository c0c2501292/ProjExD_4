import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    delta = {
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)
        self.imgs = {
            (+1, 0): img,
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),
            (-1, 0): img0,
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal" 
        self.hyper_life = 0

    def change_img(self, num: int, screen: pg.Surface):
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])

        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]

        # --- 無敵状態の処理 ---
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.image)
            self.hyper_life -= 1
            if self.hyper_life < 0:
                self.state = "normal"
        
        # 最後に1回だけ描画する
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        super().__init__()
        rad = random.randint(10, 50)
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    def __init__(self, bird: Bird):
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    def __init__(self, obj: "Bomb|Enemy", life: int):
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)
        self.state = "down"
        self.interval = random.randint(50, 300)

    def update(self):
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)
        
class Score:
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 99990
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)

class Muteki:
    """
    スコアを100点消費して、無敵モードに突入
    スコア:-100点
    発動時間:500フレーム
    """
    def __init__(self, muteki: int):
        super().__init__()
        self.muteki = muteki
        

# --- 追加機能：Lifeクラス ---
class Life:
    """
    残機数（ライフ）に関するクラス
    """
    def __init__(self, num: int):
        """
        初期残機数の設定とハート画像の生成
        """
        self.num = num
        # 40x40の空のSurfaceを作成
        self.image = pg.Surface((40, 40))
        self.image.set_colorkey((0, 0, 0)) # 黒を透過
        
        # ハートの描き方の数式
        points = [
            (16 * math.sin(t / 100) ** 3 + 20,
             -(13 * math.cos(t / 100) - 5 * math.cos(2 * t / 100) - 2 * math.cos(3 * t / 100) - math.cos(4 * t / 100)) + 20)
            for t in range(0, 628)
        ]
        # 赤色のハートをdraw
        pg.draw.polygon(self.image, (255, 0, 0), points)

    def update(self, screen: pg.Surface):
        """
        ハートが描かれたsurfaceをnum個blitする
        """
        for i in range(self.num):
            # 画面右下（右から50, 下から50）を基準に描画
            x = WIDTH - 50 - (i * 45) 
            y = HEIGHT - 50
            screen.blit(self.image, [x - 20, y - 20])

        

class Gravity(pg.sprite.Sprite):
    """
    追加機能2：重力場に関するクラス
    """
    def __init__(self, life: int):
        super().__init__()
        self.life = life
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)  # 透明度のある黒
        self.rect = self.image.get_rect()

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()

class EMP:
    """
    電磁パルス（EMP）: 発動時に存在する敵機と爆弾を無効化する
    """
    def __init__(self, enemies: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        for emy in enemies:
            emy.interval = float("inf")
            emy.image = pg.transform.laplacian(emy.image)
            emy.image.set_colorkey((0, 0, 0))

        for bomb in bombs:
            bomb.speed /= 2
            bomb.state = "inactive"

        emp_img = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(emp_img, (255, 255, 0), (0, 0, WIDTH, HEIGHT))
        emp_img.set_alpha(100)
        screen.blit(emp_img, [0, 0])
        pg.display.update()
        time.sleep(0.05)
        
def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    life = Life(3)  # 初期残機数：3

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    muteki = pg.sprite.Group()
    gravities = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    beams.add(Beam(bird))

#----------------------------------------------------------------------------------------
            # 右Shift 且つ スコア100以上 且つ まだ無敵じゃない
            # まず「キーが押されたイベントか？」を確認する
            if event.type == pg.KEYDOWN: 
                # その上で「何のキーか？」を確認する
                if event.key == pg.K_RSHIFT and score.value > 100 and bird.state == "normal":
                    score.value -= 100 #スコア消費
                    bird.state = "hyper" #無敵
                    bird.hyper_life = 500 #500フレーム維持
#----------------------------------------------------------------------------------------

                # リターンキー押下かつスコア200より大きい場合発動
                if event.key == pg.K_RETURN and score.value > 200:
                    score.value -= 200
                    gravities.add(Gravity(400))

                    
                if event.key == pg.K_e and score.value > 20:
                    score.value -= 20
                    EMP(emys, bombs, screen)
                
        screen.blit(bg_img, [0, 0])

        if tmr%200 == 0:
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                bombs.add(Bomb(emy, bird))

        # 重力場による敵機と爆弾の一掃とスコア加算
        for gravity in gravities:
            for emy in pg.sprite.spritecollide(gravity, emys, True):
                exps.add(Explosion(emy, 100))
                score.value += 10  # 敵機撃破で10点
            for bomb in pg.sprite.spritecollide(gravity, bombs, True):
                exps.add(Explosion(bomb, 50))
                score.value += 1   # 爆弾撃破で1点

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))
            score.value += 10
            bird.change_img(6, screen)

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1
            
        # こうかとんと爆弾の衝突判定
        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bird.state == "hyper":
                # 無敵モード：爆弾だけ消してスコアアップ
                exps.add(Explosion(bomb, 50)) # 爆発エフェクトを出す
                score.value += 1
            else:
                life.num -= 1  # 爆弾に当たるたびに1減らす
                bird.change_img(8, screen)
                
                if life.num < 0:  # 残機数が0になるまで死なない
                    # 通常モード：ゲームオーバー
                    bird.change_img(8, screen)
                    score.update(screen)
                    pg.display.update()
                    time.sleep(2)
                    return
        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            if hasattr(bomb, "state") and bomb.state == "inactive":
                continue
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        gravities.update()
        gravities.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        life.update(screen)  # ライフの更新と描画
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()