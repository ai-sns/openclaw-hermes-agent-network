from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.models import SecuritySchemeType
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, insert
from pydantic import BaseModel, EmailStr, validator
from typing import List, Dict, Optional, Annotated, Any
from datetime import datetime, timedelta
from io import BytesIO
import os
import random
import string
import uuid
import math
from PIL import Image, ImageDraw, ImageFont
from captcha.image import ImageCaptcha
from jose import jwt, JWTError
import hashlib
import hmac
import json

# FastAPI实例，配置文档路径
app = FastAPI(
    docs_url="/api/docs",  # 强制指定文档路径
    openapi_url="/api/openapi.json"  # 同步修改OpenAPI schema路径
)

# 数据库连接配置（使用peer认证）
DB_PASSWORD = os.getenv("DB_PASSWORD", "A@dt0734")
DATABASE_URL = f"postgresql+asyncpg://postgres:{DB_PASSWORD}@/gis_db?host=/var/run/postgresql"

# 创建异步数据库引擎
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 内存存储验证码信息（生产环境建议使用Redis）
captcha_store: Dict[str, dict] = {}
CAPTCHA_EXPIRE_SECONDS = 300  # 5分钟有效期

# 头像保存路径
AVATAR_UPLOAD_PATH = "./uploads/avatars/"

# 确保上传目录存在
os.makedirs(AVATAR_UPLOAD_PATH, exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY", "6d4e282ec81cEb7df8ea21A8554253981e79c7K426ae53e681fa3e4b6U576dcc")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

SERVER_SECRET = os.getenv("TREASURE_SERVER_SECRET", "MatrixWorld2026Secret")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login/")


# 响应模型
class DistanceResult(BaseModel):
    place1: str
    place2: str
    distance_meters: float


# 数据库会话依赖项
async def get_db():
    async with async_session() as session:
        yield session


_USERS_TABLE_COLUMNS_CACHE: Optional[set[str]] = None
_PLACES_TABLE_COLUMNS_CACHE: Optional[set[str]] = None


async def _get_users_table_columns(db: AsyncSession) -> set[str]:
    global _USERS_TABLE_COLUMNS_CACHE
    if _USERS_TABLE_COLUMNS_CACHE is not None:
        return _USERS_TABLE_COLUMNS_CACHE

    try:
        result = await db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'users'
                """
            )
        )
        _USERS_TABLE_COLUMNS_CACHE = {str(row[0]) for row in result.fetchall() if row and row[0]}
    except Exception:
        try:
            pragma_result = await db.execute(text("PRAGMA table_info(users)"))
            rows = pragma_result.mappings().all()
            cols: set[str] = set()
            for row in rows:
                name = row.get("name")
                if name:
                    cols.add(str(name))
            _USERS_TABLE_COLUMNS_CACHE = cols
        except Exception:
            _USERS_TABLE_COLUMNS_CACHE = set()

    return _USERS_TABLE_COLUMNS_CACHE


async def _users_supports_fields(db: AsyncSession, fields: List[str]) -> Dict[str, bool]:
    cols = await _get_users_table_columns(db)
    return {field: field in cols for field in fields}


async def _get_places_table_columns(db: AsyncSession) -> set[str]:
    global _PLACES_TABLE_COLUMNS_CACHE
    if _PLACES_TABLE_COLUMNS_CACHE is not None:
        return _PLACES_TABLE_COLUMNS_CACHE

    try:
        result = await db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'places'
                """
            )
        )
        _PLACES_TABLE_COLUMNS_CACHE = {str(row[0]) for row in result.fetchall() if row and row[0]}
    except Exception:
        try:
            pragma_result = await db.execute(text("PRAGMA table_info(places)"))
            rows = pragma_result.mappings().all()
            cols: set[str] = set()
            for row in rows:
                name = row.get("name")
                if name:
                    cols.add(str(name))
            _PLACES_TABLE_COLUMNS_CACHE = cols
        except Exception:
            _PLACES_TABLE_COLUMNS_CACHE = set()

    return _PLACES_TABLE_COLUMNS_CACHE


async def _places_supports_fields(db: AsyncSession, fields: List[str]) -> Dict[str, bool]:
    cols = await _get_places_table_columns(db)
    return {field: field in cols for field in fields}


def _parse_place_position_by_map(value: Any) -> Optional[list]:
    if value is None:
        return None

    if isinstance(value, list):
        return value

    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        parsed = json.loads(raw)
    except Exception:
        return None

    if not isinstance(parsed, list) or len(parsed) < 2:
        return None

    normalized: list = []
    for item in parsed:
        if not (isinstance(item, (list, tuple)) and len(item) >= 2):
            normalized.append(item)
            continue
        try:
            lng = float(item[0])
            lat = float(item[1])
            normalized.append([lng, lat])
        except Exception:
            normalized.append(list(item))

    return normalized


@app.get("/api/")
def read_root():
    return {"Hello888": "World888"}


@app.get("/api/get_initial_position/")
async def get_initial_position(db: AsyncSession = Depends(get_db)):
    """Return a base coordinate used by clients to bootstrap current_position."""
    DEFAULT_LNG = -121.88947550295555
    DEFAULT_LAT = 37.33200027587634

    lng = DEFAULT_LNG
    lat = DEFAULT_LAT

    try:
        place_row = None
        try:
            place_result = await db.execute(text("""
                SELECT
                    ST_X(place_position::geometry) AS lng,
                    ST_Y(place_position::geometry) AS lat
                FROM places
                ORDER BY random()
                LIMIT 1
            """))
            place_row = place_result.mappings().first()
        except Exception:
            place_row = None

        if place_row and place_row.get("lng") is not None and place_row.get("lat") is not None:
            lng = float(place_row.get("lng"))
            lat = float(place_row.get("lat"))
        else:
            user_row = None
            try:
                user_result = await db.execute(text("""
                    SELECT
                        ST_X(location::geometry) AS lng,
                        ST_Y(location::geometry) AS lat
                    FROM users
                    WHERE status = 1
                    ORDER BY random()
                    LIMIT 1
                """))
                user_row = user_result.mappings().first()
            except Exception:
                user_row = None

            if user_row and user_row.get("lng") is not None and user_row.get("lat") is not None:
                lng = float(user_row.get("lng"))
                lat = float(user_row.get("lat"))
    except Exception:
        lng = DEFAULT_LNG
        lat = DEFAULT_LAT

    if not (-180.0 <= lng <= 180.0 and -90.0 <= lat <= 90.0):
        lng = DEFAULT_LNG
        lat = DEFAULT_LAT

    return {"success": True, "data": {"lng": lng, "lat": lat}}


@app.get("/api/distance", response_model=List[DistanceResult])
async def calculate_distance(
        place1: str = 'Home',
        place2: str = 'Work',
        db: AsyncSession = Depends(get_db)
):
    """
    计算两个地点之间的地理距离（米）
    默认查询Home和Work的地点组合
    """
    query = text("""
    SELECT 
        a.name AS place1,
        b.name AS place2,
        ST_Distance(a.geom::geography, b.geom::geography) AS distance_meters
    FROM places a, places b
    WHERE a.name = :name1 AND b.name = :name2;
    """)

    try:
        result = await db.execute(query, {'name1': place1, 'name2': place2})
        return [dict(row) for row in result.mappings()]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


def generate_captcha_code(length: int = 6) -> str:
    """生成一个随机的字母数字验证码文本"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_captcha_image(captcha_code: str) -> BytesIO:
    """生成验证码图像并返回图像的字节流"""
    image = ImageCaptcha()
    data = image.generate(captcha_code)
    return data


@app.get("/api/captcha/")
async def get_captcha():
    captcha_code = generate_captcha_code()
    captcha_image_data = generate_captcha_image(captcha_code)
    print("captcha_code", captcha_code)
    # 将验证码文本存储在内存中
    captcha_id = uuid.uuid4().hex
    captcha_store[captcha_id] = {
        "code": captcha_code,
        "expire_at": datetime.now() + timedelta(seconds=CAPTCHA_EXPIRE_SECONDS)
    }

    return StreamingResponse(captcha_image_data, media_type="image/png", headers={"X-Captcha-ID": captcha_id})


class UserRegisterRequest(BaseModel):
    nation_id: str
    password: str
    account: str
    longitude: float
    latitude: float
    captcha_id: str
    captcha_code: str
    nick_name: str
    avatar: str
    avatar_3d: str
    profile: str
    sns_url: str
    status: int
    a2a_endpoint: Optional[str] = None

    @validator('password')
    def password_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

    @validator('account')
    def account_validation(cls, v):
        if not v:
            raise ValueError('Account cannot be empty')
        return v


def generate_random_nation_id() -> str:
    """生成一个以AI开头的20位随机字符串"""
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))
    return f"AI000000{random_suffix}"


@app.post("/api/register/")
async def register_user(
        nation_id: Annotated[str, Form()],
        password: Annotated[str, Form()],
        account: Annotated[str, Form()],
        longitude: Annotated[float, Form()],
        latitude: Annotated[float, Form()],
        captcha_id: Annotated[str, Form()],
        captcha_code: Annotated[str, Form()],
        nick_name: Annotated[str, Form()],
        avatar: Annotated[str, Form()],
        avatar_3d: Annotated[str, Form()],
        profile: Annotated[str, Form()],
        sns_url: Annotated[str, Form()],
        status: Annotated[int, Form()],
        framework: Annotated[Optional[str], Form()] = None,
        model: Annotated[Optional[str], Form()] = None,
        a2a_endpoint: Annotated[Optional[str], Form()] = None,
        avatar_file: UploadFile = File(...),  # 接收上传的头像文件
        db: AsyncSession = Depends(get_db)
):
    """
    用户注册接口，包含验证码验证和用户信息存储
    """
    captcha_info = captcha_store.get(captcha_id)
    if not captcha_info:
        raise HTTPException(status_code=400, detail="Invalid captcha ID")

    if datetime.now() > captcha_info["expire_at"]:
        del captcha_store[captcha_id]
        raise HTTPException(status_code=401, detail="Captcha expired")

    if captcha_code.upper() != captcha_info["code"]:
        raise HTTPException(status_code=402, detail="Invalid captcha code")

    del captcha_store[captcha_id]

    if not nation_id:
        nation_id = generate_random_nation_id()

    existing_by_account = await db.execute(
        text("SELECT nation_id, password FROM users WHERE account = :account"),
        {"account": account}
    )
    existing_row = existing_by_account.mappings().first()
    user_exist = bool(existing_row)
    if existing_row:
        existing_nation_id = existing_row.get("nation_id")
        existing_password = existing_row.get("password")
        if existing_password is not None and hash_password(password) != existing_password:
            raise HTTPException(status_code=401, detail="The XMPP account exists on the AI-SNS server, but the ai-sns password does not match.")
        if existing_nation_id:
            nation_id = str(existing_nation_id)

    try:

        supported = await _users_supports_fields(db, [
            "framework",
            "model",
            "a2a_endpoint",
            "avatar_3d",
            "profile",
            "sns_url",
        ])
        framework_value: Optional[str] = (framework.strip() if isinstance(framework, str) else framework)
        if framework_value is not None:
            framework_value = str(framework_value).strip() or None

        model_value: Optional[str] = (model.strip() if isinstance(model, str) else model)
        if model_value is not None:
            model_value = str(model_value).strip() or None

        a2a_endpoint_value: Optional[str] = (a2a_endpoint.strip() if isinstance(a2a_endpoint, str) else a2a_endpoint)
        if a2a_endpoint_value is not None:
            a2a_endpoint_value = str(a2a_endpoint_value).strip() or None

        default_framework = "AI-SNS"
        default_model = "gpt-4o-mini"

        avatar_filename = f"{nation_id}_avatar.png"
        avatar_file_path = os.path.join(AVATAR_UPLOAD_PATH, avatar_filename)

        with open(avatar_file_path, "wb") as f:
            f.write(await avatar_file.read())

        lon_str = str(longitude)
        lat_str = str(latitude)
        wkt_point = f"POINT({lon_str} {lat_str})"

        if user_exist:
            set_parts = [
                "location = ST_GeomFromText(:wkt_point, 4326)",
                "nick_name = :nick_name",
                "avatar = :avatar",
                "status = 1",
                "create_time = NOW()",
            ]

            params = {
                "nation_id": nation_id,
                "wkt_point": wkt_point,
                "nick_name": nick_name,
                "avatar": avatar,
            }
            if supported.get("avatar_3d"):
                set_parts.append("avatar_3d = :avatar_3d")
                params["avatar_3d"] = avatar_3d
            if supported.get("profile"):
                set_parts.append("profile = :profile")
                params["profile"] = profile
            if supported.get("sns_url"):
                set_parts.append("sns_url = :sns_url")
                params["sns_url"] = sns_url
            if supported.get("framework") and framework is not None:
                set_parts.append("framework = :framework")
                params["framework"] = framework_value
            if supported.get("model") and model is not None:
                set_parts.append("model = :model")
                params["model"] = model_value
            if supported.get("a2a_endpoint") and a2a_endpoint is not None:
                set_parts.append("a2a_endpoint = :a2a_endpoint")
                params["a2a_endpoint"] = a2a_endpoint_value

            sql = text(
                f"""
                UPDATE users
                SET {', '.join(set_parts)}
                WHERE nation_id = :nation_id
                """
            )
            await db.execute(sql, params)
        else:
            columns = [
                "nation_id",
                "password",
                "account",
                "location",
                "nick_name",
                "avatar",
                "status",
                "create_time",
            ]
            values = [
                ":nation_id",
                ":password",
                ":account",
                "ST_GeomFromText(:wkt_point, 4326)",
                ":nick_name",
                ":avatar",
                "1",
                "NOW()",
            ]
            params = {
                "nation_id": nation_id,
                "password": hash_password(password),
                "account": account,
                "wkt_point": wkt_point,
                "nick_name": nick_name,
                "avatar": avatar,
            }
            if supported.get("avatar_3d"):
                columns.append("avatar_3d")
                values.append(":avatar_3d")
                params["avatar_3d"] = avatar_3d
            if supported.get("profile"):
                columns.append("profile")
                values.append(":profile")
                params["profile"] = profile
            if supported.get("sns_url"):
                columns.append("sns_url")
                values.append(":sns_url")
                params["sns_url"] = sns_url
            if supported.get("framework"):
                columns.append("framework")
                values.append(":framework")
                params["framework"] = framework_value or default_framework
            if supported.get("model"):
                columns.append("model")
                values.append(":model")
                params["model"] = model_value or default_model
            if supported.get("a2a_endpoint") and a2a_endpoint_value is not None:
                columns.append("a2a_endpoint")
                values.append(":a2a_endpoint")
                params["a2a_endpoint"] = a2a_endpoint_value

            sql = text(
                f"""
                INSERT INTO users ({', '.join(columns)})
                VALUES ({', '.join(values)})
                """
            )
            await db.execute(sql, params)

        await db.commit()

        return JSONResponse(
            status_code=201 if not user_exist else 200,
            content={"message": "User registered successfully" if not user_exist else "User updated successfully", "nation_id": nation_id}
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


def hash_password(password: str) -> str:
    """简单的密码哈希演示函数，实际应用中应该使用bcrypt或类似库"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


class UserResponse(BaseModel):
    nation_id: str
    account: str
    location: List[float]
    nick_name: str
    avatar: str
    avatar_3d: str
    profile: str
    sns_url: str
    a2a_endpoint: Optional[str] = None
    level: int = 0
    membership: int = 0
    framework: Optional[str] = None
    model: Optional[str] = None


# 新增：生成访问令牌和刷新令牌
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 新增：登录用户并返回令牌
@app.post("/api/login/")
async def login(username: str = Form("AI000000BGRWDKCEGZNOBN4ATA9A"),
                password: str = Form("securePassword123!"),
                db: AsyncSession = Depends(get_db)
                ):
    # 验证用户凭证
    nation_id = username
    result = await db.execute(
        text("SELECT password FROM users WHERE nation_id = :nation_id"),
        {"nation_id": nation_id}
    )
    user = result.scalar()

    if not user or hash_password(password) != user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": nation_id}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": nation_id}, expires_delta=refresh_token_expires
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@app.post("/api/refresh-token/")
async def refresh_access_token(refresh_token: str = Form(...)):
    """
    使用刷新令牌获取新的访问令牌
    """
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成新的访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)

    return {"access_token": access_token}


@app.post("/api/upload_avatar/")
async def upload_avatar(
        nation_id: Annotated[str, Form()],
        avatar_file: UploadFile = File(...),  # 接收上传的头像文件
        db: AsyncSession = Depends(get_db)
):
    """
    用户头像上传接口
    """
    try:
        # 生成头像文件名
        avatar_filename = f"{nation_id}_avatar.png"
        avatar_file_path = os.path.join(AVATAR_UPLOAD_PATH, avatar_filename)

        # 保存上传的头像文件
        with open(avatar_file_path, "wb") as f:
            f.write(await avatar_file.read())

        # 更新数据库中用户的头像信息
        set_parts = ["avatar = :avatar"]
        params: Dict[str, Any] = {"nation_id": nation_id, "avatar": avatar_filename}

        sql = text(
            f"""
            UPDATE users
            SET {', '.join(set_parts)}
            WHERE nation_id = :nation_id
            """
        )
        await db.execute(sql, params)

        await db.commit()

        return JSONResponse(
            status_code=200,
            content={"message": "Avatar uploaded successfully", "avatar": avatar_filename}
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Avatar upload failed: {str(e)}")


@app.post("/api/update-location/")
async def update_location(
        nation_id: str = Form(...),
        password: str = Form(...),
        longitude: float = Form(...),
        latitude: float = Form(...),
        db: AsyncSession = Depends(get_db)
):
    """
    更新用户的地理位置（location 字段）
    - 使用 nation_id + password 验证身份
    - 改为 POST 调用
    """
    hashed_pwd = hash_password(password)
    wkt_point = f"POINT({longitude} {latitude})"

    set_parts = ["location = ST_GeomFromText(:wkt_point, 4326)"]
    params: Dict[str, Any] = {
        "wkt_point": wkt_point,
        "nation_id": nation_id,
        "hashed_pwd": hashed_pwd,
    }

    result = await db.execute(
        text(
            f"""UPDATE users
                SET {', '.join(set_parts)}
                WHERE nation_id = :nation_id
                AND password = :hashed_pwd"""
        ),
        params,
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await db.commit()
    return {"message": "Location updated successfully"}


@app.post("/api/update-profession/")
async def update_profession(
        nation_id: str = Form(...),
        password: str = Form(...),
        profession: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    """
    更新用户的职业（profession 字段）
    - 使用 nation_id + password 验证身份
    - 改为 POST 调用
    """
    hashed_pwd = hash_password(password)

    set_parts = ["profession = :profession"]
    params: Dict[str, Any] = {
        "profession": profession,
        "nation_id": nation_id,
        "hashed_pwd": hashed_pwd,
    }

    result = await db.execute(
        text(
            f"""UPDATE users
                SET {', '.join(set_parts)}
                WHERE nation_id = :nation_id
                AND password = :hashed_pwd"""
        ),
        params,
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=401, detail="Username or password wrong.")

    await db.commit()
    return {"message": "Profession updated successfully"}


# 新增：获取附近用户（包含JWT验证）
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username


async def validate_geo_coordinates(longitude: float, latitude: float):
    """验证地理坐标是否有效"""
    if not (-180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid longitude value, must be between -180 and 180")
    if not (-90 <= latitude <= 90):
        raise HTTPException(status_code=400, detail="Invalid latitude value, must be between -90 and 90")


async def extract_location_params(
        request: Request,
        lng: Optional[float],
        lat: Optional[float],
        max_distance: Optional[int],
        limit: Optional[int]
):
    body: Any = {}
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            body = {}

    if not isinstance(body, dict):
        body = {}

    lng_value = body.get("lng", body.get("longitude", lng))
    lat_value = body.get("lat", body.get("latitude", lat))
    max_distance_value = body.get("max_distance")
    if max_distance_value is None:
        max_distance_value = max_distance
    limit_value = body.get("limit")
    if limit_value is None:
        limit_value = limit

    if lng_value is None or lat_value is None:
        raise HTTPException(status_code=422, detail="lng and lat are required")

    try:
        lng_value = float(lng_value)
        lat_value = float(lat_value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="lng and lat must be numbers")

    if max_distance_value is None:
        max_distance_value = 50000000
    if limit_value is None:
        limit_value = 100

    try:
        max_distance_value = int(max_distance_value)
        limit_value = int(limit_value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="max_distance and limit must be integers")

    if max_distance_value <= 0:
        raise HTTPException(status_code=400, detail="Max distance must be positive")
    if limit_value <= 0:
        raise HTTPException(status_code=400, detail="Limit must be positive")

    await validate_geo_coordinates(lng_value, lat_value)
    return lng_value, lat_value, max_distance_value, limit_value


async def execute_nearby_users_query(db: AsyncSession, longitude: float, latitude: float, max_distance: int, limit: int):
    """执行附近用户查询并返回结果"""
    supported = await _users_supports_fields(db, ["level", "membership", "framework", "model", "a2a_endpoint"])
    extra_parts: List[str] = []
    if supported.get("level"):
        extra_parts.append("level")
    if supported.get("membership"):
        extra_parts.append("membership")
    if supported.get("framework"):
        extra_parts.append("framework")
    if supported.get("model"):
        extra_parts.append("model")
    if supported.get("a2a_endpoint"):
        extra_parts.append("a2a_endpoint")
    extra_select = "" if not extra_parts else ",\n        " + ",\n        ".join(extra_parts)

    query = text("""
    SELECT 
        nation_id,
        account,
        nick_name,
        avatar,
        avatar_3d,
        profile,
        sns_url,
        profession{extra_select},
        ST_X(location::geometry) AS longitude,
        ST_Y(location::geometry) AS latitude,
        ST_Distance(
            ST_Transform(location::geometry, 3857),
            ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857)
        ) AS distance_meters
    FROM users
    WHERE status = 1 
      AND ST_DWithin(
        ST_Transform(location::geometry, 3857),
        ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857),
        :max_dist
      )
    ORDER BY distance_meters ASC
    LIMIT :limit
    """.format(extra_select=extra_select))

    result = await db.execute(query, {
        'lon': longitude,
        'lat': latitude,
        'max_dist': max_distance,
        'limit': limit
    })

    rows = result.mappings().all()
    content = []
    for row in rows:
        level_value = int(row.get("level") or 0) if supported.get("level") else 0
        membership_value = int(row.get("membership") or 0) if supported.get("membership") else 0
        framework_value = row.get("framework") if supported.get("framework") else None
        model_value = row.get("model") if supported.get("model") else None
        a2a_endpoint_value = row.get("a2a_endpoint") if supported.get("a2a_endpoint") else None
        content.append(
            {
                "nation_id": row.get("nation_id"),
                "account": row.get("account"),
                "location": [row.get("longitude"), row.get("latitude")],
                "nick_name": row.get("nick_name"),
                "avatar": row.get("avatar"),
                "avatar_3d": row.get("avatar_3d"),
                "profile": row.get("profile"),
                "sns_url": row.get("sns_url"),
                "a2a_endpoint": a2a_endpoint_value,
                "level": level_value,
                "membership": membership_value,
                "framework": framework_value,
                "model": model_value,
            }
        )

    return content


@app.get("/api/get_nearest_people/", response_model=List[UserResponse])
async def get_nearby_users(
        longitude: float = 116.27882,
        latitude: float = 39.71164,
        max_distance: int = 5000,
        limit: int = 100,
        db: AsyncSession = Depends(get_db)
):
    """
    获取指定经纬度附近的人员列表
    - longitude: 经度，范围-180到180
    - latitude: 纬度，范围-90到90
    - max_distance: 最大距离(米)，必须为正数
    - limit: 返回结果最大数量
    """
    await validate_geo_coordinates(longitude, latitude)
    if max_distance <= 0:
        raise HTTPException(status_code=400, detail="Max distance must be positive")
    try:
        return await execute_nearby_users_query(db, longitude, latitude, max_distance, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/get_nearest_people_v2/", response_model=List[UserResponse])
async def get_nearby_users_v2(
        longitude: float = 116.27882,
        latitude: float = 39.71164,
        max_distance: int = 5000,
        limit: int = 100,
        db: AsyncSession = Depends(get_db),
        token: str = Depends(oauth2_scheme)
):
    """
    获取指定经纬度附近的人员列表（需要身份验证）
    - 参数同上
    """
    await get_current_user(token)  # 验证token
    await validate_geo_coordinates(longitude, latitude)
    if max_distance <= 0:
        raise HTTPException(status_code=400, detail="Max distance must be positive")
    try:
        return await execute_nearby_users_query(db, longitude, latitude, max_distance, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/api/update-user/")
async def update_user_post(
        nation_id: str = Form("AI000000BGRWDKCEGZNOBN4ATA9A"),
        password: str = Form("securePassword123!"),
        account: Optional[str] = Form(None),
        nick_name: Optional[str] = Form(None),
        avatar_3d: Optional[str] = Form(None),
        profile: Optional[str] = Form(None),
        sns_url: Optional[str] = Form(None),
        framework: Optional[str] = Form(None),
        model: Optional[str] = Form(None),
        a2a_endpoint: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    # 必须字段参数验证和处理
    hashed_pwd = hash_password(password)

    # 构建动态SQL参数和条件
    update_fields = {}
    if account is not None:
        update_fields["account"] = account
    if nick_name is not None:
        update_fields["nick_name"] = nick_name
    if avatar_3d is not None:
        update_fields["avatar_3d"] = avatar_3d
    if profile is not None:
        update_fields["profile"] = profile
    if sns_url is not None:
        update_fields["sns_url"] = sns_url

    supported = await _users_supports_fields(db, ["framework", "model", "a2a_endpoint"])
    if supported.get("framework") and framework is not None:
        update_fields["framework"] = framework
    if supported.get("model") and model is not None:
        update_fields["model"] = model
    if supported.get("a2a_endpoint") and a2a_endpoint is not None:
        update_fields["a2a_endpoint"] = a2a_endpoint

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    # 构建动态SQL的SET部分
    set_clause = ", ".join(f"{key} = :{key}" for key in update_fields.keys())

    # 执行带条件的动态UPDATE语句
    query = text(f"""UPDATE users 
                     SET {set_clause} 
                     WHERE nation_id = :nation_id 
                     AND password = :hashed_pwd""")
    params = {**update_fields, "nation_id": nation_id, "hashed_pwd": hashed_pwd}

    result = await db.execute(query, params)

    # 检查受影响行数
    if result.rowcount == 0:
        raise HTTPException(status_code=401, detail="Username or password wrong.")

    await db.commit()
    return {"message": "User information updated successfully"}


@app.post("/api/change-password/")
async def change_password(
        nation_id: str = Form(...),
        old_password: str = Form(...),
        new_password: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    """
    修改用户密码接口
    - nation_id: 用户ID
    - old_password: 旧密码
    - new_password: 新密码
    """
    # 验证新密码强度
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")

    # 验证旧密码是否正确
    old_hashed_pwd = hash_password(old_password)

    # 查询用户并验证旧密码
    result = await db.execute(
        text("SELECT 1 FROM users WHERE nation_id = :nation_id AND password = :hashed_pwd"),
        {"nation_id": nation_id, "hashed_pwd": old_hashed_pwd}
    )

    user = result.scalar()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid nation_id or old password")

    # 更新密码
    new_hashed_pwd = hash_password(new_password)
    await db.execute(
        text("UPDATE users SET password = :new_hashed_pwd WHERE nation_id = :nation_id"),
        {"new_hashed_pwd": new_hashed_pwd, "nation_id": nation_id}
    )

    await db.commit()

    return {"message": "Password changed successfully"}


@app.post("/api/get_service_list/")
async def get_service_list(
        request: Request,
        lng: Optional[float] = Form(None),
        lat: Optional[float] = Form(None),
        max_distance: Optional[int] = Form(None),
        limit: Optional[int] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    """
    从 services 表获取服务列表
    返回 JSON 格式与原先固定数据一致
    """
    try:
        max_distance_value = 5000 if max_distance is None else max_distance
        lng, lat, max_distance, limit = await extract_location_params(request, lng, lat, max_distance_value, limit)
        query = text("""
            SELECT 
                service_id AS id,
                name,
                description,
                place,
                ST_X(position::geometry) AS lng,
                ST_Y(position::geometry) AS lat,
                type,
                address,
                method,
                parameter,
                ST_Distance(
                    ST_Transform(position::geometry, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857)
                ) AS distance_meters
            FROM services
            WHERE ST_DWithin(
                ST_Transform(position::geometry, 3857),
                ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857),
                :max_dist
            )
            ORDER BY distance_meters ASC
            LIMIT :limit
        """)
        result = await db.execute(query, {"lon": lng, "lat": lat, "max_dist": max_distance, "limit": limit})
        content = []
        for row in result.mappings():
            param = row["parameter"]
            # JSONB字段直接返回JSON对象，如果是字符串"None"，保持一致
            if isinstance(param, str) and param == "None":
                param_value = "None"
            else:
                param_value = param
            content.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "place": row["place"],
                "lng": row["lng"],
                "lat": row["lat"],
                "type": row["type"],
                "address": row["address"],
                "method": row["method"],
                "parameter": param_value
            })
        return JSONResponse(status_code=200, content=content)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Get service list failed: {str(e)}")


@app.post("/api/get_people_list/")
async def get_people_list(
        request: Request,
        lng: Optional[float] = Form(None),
        lat: Optional[float] = Form(None),
        max_distance: Optional[int] = Form(None),
        limit: Optional[int] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    """
    从 users 表获取用户列表
    返回 JSON 格式与原先固定数据一致
    """
    try:
        max_distance_value = 50000000 if max_distance is None else max_distance
        lng, lat, max_distance, limit = await extract_location_params(request, lng, lat, max_distance_value, limit)

        supported = await _users_supports_fields(db, ["level", "membership", "framework", "model", "a2a_endpoint"])
        extra_parts: List[str] = []
        if supported.get("level"):
            extra_parts.append("level")
        if supported.get("membership"):
            extra_parts.append("membership")
        if supported.get("framework"):
            extra_parts.append("framework")
        if supported.get("model"):
            extra_parts.append("model")
        if supported.get("a2a_endpoint"):
            extra_parts.append("a2a_endpoint")
        extra_select = "" if not extra_parts else ",\n                " + ",\n                ".join(extra_parts)

        query = text("""
            SELECT 
                nation_id,
                account,
                nick_name,
                avatar,
                avatar_3d,
                profile,
                sns_url,
                profession{extra_select},
                ST_X(location::geometry) AS lng,
                ST_Y(location::geometry) AS lat,
                ST_Distance(
                    ST_Transform(location::geometry, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857)
                ) AS distance_meters
            FROM users
            WHERE status = 1
              AND ST_DWithin(
                ST_Transform(location::geometry, 3857),
                ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857),
                :max_dist
              )
            ORDER BY distance_meters ASC
            LIMIT :limit
        """.format(extra_select=extra_select))
        result = await db.execute(query, {"lon": lng, "lat": lat, "max_dist": max_distance, "limit": limit})
        content = []
        for row in result.mappings():
            level_value = int(row.get("level") or 0) if supported.get("level") else 0
            membership_value = int(row.get("membership") or 0) if supported.get("membership") else 0
            framework_value = row.get("framework") if supported.get("framework") else None
            model_value = row.get("model") if supported.get("model") else None
            a2a_endpoint_value = row.get("a2a_endpoint") if supported.get("a2a_endpoint") else None
            content.append({
                "nation_id": row["nation_id"],
                "account": row["account"],
                "location": [row["lng"], row["lat"]],
                "nick_name": row["nick_name"],
                "avatar": row["avatar"],
                "avatar_3d": row["avatar_3d"],
                "profile": row["profile"],
                "sns_url": row["sns_url"],
                "profession": row["profession"],
                "a2a_endpoint": a2a_endpoint_value,
                "level": level_value,
                "membership": membership_value,
                "framework": framework_value,
                "model": model_value,
            })
        return JSONResponse(status_code=200, content=content)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Get people list failed: {str(e)}")


async def execute_nearest_profession_user_query(
        db: AsyncSession,
        longitude: float,
        latitude: float,
        max_distance: int,
        profession: str,
        exclude_nation_id: Optional[str] = None,
):
    supported = await _users_supports_fields(db, ["level", "membership", "framework", "model", "a2a_endpoint"])
    extra_parts: List[str] = []
    if supported.get("level"):
        extra_parts.append("level")
    if supported.get("membership"):
        extra_parts.append("membership")
    if supported.get("framework"):
        extra_parts.append("framework")
    if supported.get("model"):
        extra_parts.append("model")
    if supported.get("a2a_endpoint"):
        extra_parts.append("a2a_endpoint")
    extra_select = "" if not extra_parts else ",\n            " + ",\n            ".join(extra_parts)

    query = text("""
        SELECT
            nation_id,
            account,
            nick_name,
            avatar,
            avatar_3d,
            profile,
            sns_url,
            profession{extra_select},
            ST_X(location::geometry) AS lng,
            ST_Y(location::geometry) AS lat,
            ST_Distance(
                ST_Transform(location::geometry, 3857),
                ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857)
            ) AS distance_meters
        FROM users
        WHERE status = 1
          AND (:exclude_nation_id IS NULL OR nation_id <> :exclude_nation_id)
          AND lower(coalesce(profession, '')) = lower(:profession)
          AND ST_DWithin(
            ST_Transform(location::geometry, 3857),
            ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857),
            :max_dist
          )
        ORDER BY distance_meters ASC
        LIMIT 1
    """.format(extra_select=extra_select))

    result = await db.execute(query, {
        "lon": longitude,
        "lat": latitude,
        "max_dist": max_distance,
        "profession": profession,
        "exclude_nation_id": exclude_nation_id,
    })
    row = result.mappings().first()
    if not row:
        return None

    level_value = int(row.get("level") or 0) if supported.get("level") else 0
    membership_value = int(row.get("membership") or 0) if supported.get("membership") else 0
    framework_value = row.get("framework") if supported.get("framework") else None
    model_value = row.get("model") if supported.get("model") else None
    a2a_endpoint_value = row.get("a2a_endpoint") if supported.get("a2a_endpoint") else None

    return {
        "nation_id": row["nation_id"],
        "account": row["account"],
        "location": [row["lng"], row["lat"]],
        "nick_name": row["nick_name"],
        "avatar": row["avatar"],
        "avatar_3d": row["avatar_3d"],
        "profile": row["profile"],
        "sns_url": row["sns_url"],
        "profession": row["profession"],
        "distance_meters": row["distance_meters"],
        "a2a_endpoint": a2a_endpoint_value,
        "level": level_value,
        "membership": membership_value,
        "framework": framework_value,
        "model": model_value,
    }


@app.post("/api/get_nearest_people_by_profession/")
async def get_nearest_people_by_profession(
        request: Request,
        profession: Optional[str] = Form(None),
        exclude_nation_id: Optional[str] = Form(None),
        lng: Optional[float] = Form(None),
        lat: Optional[float] = Form(None),
        max_distance: Optional[int] = Form(None),
        db: AsyncSession = Depends(get_db),
):
    """
    Return the nearest active user filtered by profession.

    Accepts both form fields and JSON body.
    Required:
      - profession
      - lng / lat
    Optional:
      - max_distance (meters)
      - exclude_nation_id
    """
    try:
        # Reuse existing lng/lat/max_distance parsing rules
        lng_value, lat_value, max_distance_value, _limit_value = await extract_location_params(
            request=request,
            lng=lng,
            lat=lat,
            max_distance=max_distance,
            limit=1,
        )

        body: Any = {}
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body = await request.json()
            except Exception:
                body = {}
        if not isinstance(body, dict):
            body = {}

        profession_value = (body.get("profession", profession) or "").strip()
        exclude_value = (body.get("exclude_nation_id", exclude_nation_id) or None)
        if exclude_value is not None:
            exclude_value = str(exclude_value).strip() or None

        if not profession_value:
            raise HTTPException(status_code=422, detail="profession is required")

        user = await execute_nearest_profession_user_query(
            db=db,
            longitude=lng_value,
            latitude=lat_value,
            max_distance=max_distance_value,
            profession=profession_value,
            exclude_nation_id=exclude_value,
        )

        return JSONResponse(status_code=200, content=user)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Get nearest people by profession failed: {str(e)}")


@app.post("/api/get_place_list/")
async def get_place_list(
        request: Request,
        lng: Optional[float] = Form(None),
        lat: Optional[float] = Form(None),
        max_distance: Optional[int] = Form(None),
        limit: Optional[int] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    """
    从 places 表获取地点列表
    返回 JSON 格式与原先固定数据一致
    """
    try:
        max_distance_value = 5000 if max_distance is None else max_distance
        lng, lat, max_distance, limit = await extract_location_params(request, lng, lat, max_distance_value, limit)
        supported_places = await _places_supports_fields(db, ["url_3d", "place_position_by_map"])
        place_extra_parts: List[str] = []
        if supported_places.get("url_3d"):
            place_extra_parts.append("url_3d")
        if supported_places.get("place_position_by_map"):
            place_extra_parts.append("place_position_by_map")
        place_extra_select = "" if not place_extra_parts else ",\n                " + ",\n                ".join(place_extra_parts)

        query = text("""
            SELECT 
                place_id,
                place_name,
                ST_X(place_position::geometry) AS lng,
                ST_Y(place_position::geometry) AS lat,
                url{place_extra_select},
                description,
                ST_Distance(
                    ST_Transform(place_position::geometry, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857)
                ) AS distance_meters
            FROM places
            WHERE ST_DWithin(
                ST_Transform(place_position::geometry, 3857),
                ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857),
                :max_dist
            )
            ORDER BY distance_meters ASC
            LIMIT :limit
        """.format(place_extra_select=place_extra_select))

        result = await db.execute(query, {"lon": lng, "lat": lat, "max_dist": max_distance, "limit": limit})
        content = []
        for row in result.mappings():
            url_3d_value = row.get("url_3d") if supported_places.get("url_3d") else None
            ppm_raw = row.get("place_position_by_map") if supported_places.get("place_position_by_map") else None
            ppm_value = _parse_place_position_by_map(ppm_raw)
            content.append({
                "place_id": row["place_id"],
                "place_name": row["place_name"],
                "place_position": [row["lng"], row["lat"]],
                "place_position_by_map": ppm_value,
                "url": row["url"],
                "url_3d": url_3d_value,
                "description": row["description"]
            })
        return JSONResponse(status_code=200, content=content)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Get place list failed: {str(e)}")


@app.post("/api/get_guidance_lists/")
async def get_guidance_lists(
        request: Request,
        lng: Optional[float] = Form(None),
        lat: Optional[float] = Form(None),
        max_distance: Optional[int] = Form(None),
        db: AsyncSession = Depends(get_db),
):
    try:
        lng_value, lat_value, max_distance_value, _ = await extract_location_params(request, lng, lat, max_distance, limit=None)
        min_distance_meters = max_distance_value

        supported = await _users_supports_fields(db, ["level", "membership", "framework", "model", "a2a_endpoint"])
        extra_parts: List[str] = []
        if supported.get("level"):
            extra_parts.append("level")
        if supported.get("membership"):
            extra_parts.append("membership")
        if supported.get("framework"):
            extra_parts.append("framework")
        if supported.get("model"):
            extra_parts.append("model")
        if supported.get("a2a_endpoint"):
            extra_parts.append("a2a_endpoint")
        extra_select = "" if not extra_parts else ",\n                " + ",\n                ".join(extra_parts)

        supported_places = await _places_supports_fields(db, ["url_3d", "place_position_by_map"])
        place_extra_parts: List[str] = []
        if supported_places.get("url_3d"):
            place_extra_parts.append("url_3d")
        if supported_places.get("place_position_by_map"):
            place_extra_parts.append("place_position_by_map")
        place_extra_select = "" if not place_extra_parts else ",\n                " + ",\n                ".join(place_extra_parts)

        people_query = text("""
            SELECT
                nation_id,
                account,
                nick_name,
                avatar,
                avatar_3d,
                profile,
                sns_url,
                profession{extra_select},
                ST_X(location::geometry) AS lng,
                ST_Y(location::geometry) AS lat,
                ST_Distance(
                    ST_Transform(location::geometry, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857)
                ) AS distance_meters
            FROM users
            WHERE status = 1
              AND ST_Distance(
                    ST_Transform(location::geometry, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857)
                ) > :min_dist
            ORDER BY distance_meters ASC
            LIMIT 5
        """.format(extra_select=extra_select))

        place_query = text("""
            SELECT
                place_id,
                place_name,
                ST_X(place_position::geometry) AS lng,
                ST_Y(place_position::geometry) AS lat,
                description,
                url{place_extra_select},
                ST_Distance(
                    ST_Transform(place_position::geometry, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857)
                ) AS distance_meters
            FROM places
            WHERE ST_Distance(
                    ST_Transform(place_position::geometry, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3857)
                ) > :min_dist
            ORDER BY distance_meters ASC
            LIMIT 5
        """.format(place_extra_select=place_extra_select))

        params = {
            "lon": lng_value,
            "lat": lat_value,
            "min_dist": min_distance_meters,
        }

        people_result = await db.execute(people_query, params)
        people_list = []
        for row in people_result.mappings():
            level_value = int(row.get("level") or 0) if supported.get("level") else 0
            membership_value = int(row.get("membership") or 0) if supported.get("membership") else 0
            framework_value = row.get("framework") if supported.get("framework") else None
            model_value = row.get("model") if supported.get("model") else None
            a2a_endpoint_value = row.get("a2a_endpoint") if supported.get("a2a_endpoint") else None
            people_list.append({
                "nation_id": row["nation_id"],
                "account": row["account"],
                "location": [row["lng"], row["lat"]],
                "nick_name": row["nick_name"],
                "avatar": row["avatar"],
                "avatar_3d": row["avatar_3d"],
                "profile": row["profile"],
                "sns_url": row["sns_url"],
                "profession": row["profession"],
                "distance_meters": row["distance_meters"],
                "a2a_endpoint": a2a_endpoint_value,
                "level": level_value,
                "membership": membership_value,
                "framework": framework_value,
                "model": model_value,
            })

        place_result = await db.execute(place_query, params)
        place_list = []
        for row in place_result.mappings():
            url_3d_value = row.get("url_3d") if supported_places.get("url_3d") else None
            url_value = row.get("url")
            ppm_raw = row.get("place_position_by_map") if supported_places.get("place_position_by_map") else None
            ppm_value = _parse_place_position_by_map(ppm_raw)
            place_list.append({
                "place_id": row["place_id"],
                "place_name": row["place_name"],
                "place_position": [row["lng"], row["lat"]],
                "place_position_by_map": ppm_value,
                "description": row["description"],
                "url": url_value,
                "url_3d": url_3d_value,
                "distance_meters": row["distance_meters"],
            })

        people_lines = []
        for item in people_list:
            lng_i, lat_i = (item.get("location") or [None, None])[:2]
            try:
                km = float(item.get("distance_meters") or 0) / 1000.0
            except Exception:
                km = 0.0
            nick = (item.get("nick_name") or "").strip() or (item.get("account") or "").strip() or "Unknown"
            profile = (item.get("profile") or "").strip()
            if not profile:
                profession = (item.get("profession") or "").strip()
                profile = f"Profession: {profession}" if profession else "No profile"
            people_lines.append(f"- {nick}: {profile}, coordinates [{lng_i},{lat_i}], distance {km:.1f} km\n")
        people_list_str = "".join(people_lines)

        place_lines = []
        for item in place_list:
            lng_i, lat_i = (item.get("place_position") or [None, None])[:2]
            try:
                km = float(item.get("distance_meters") or 0) / 1000.0
            except Exception:
                km = 0.0
            name = (item.get("place_name") or "").strip() or "Unknown"
            desc = (item.get("description") or "").strip() or "No description"
            place_lines.append(f"- {name}: {desc}. Coordinates [{lng_i},{lat_i}], distance {km:.1f} km.\n")
        place_list_str = "".join(place_lines)

        return JSONResponse(status_code=200, content={
            "people_list_str": people_list_str,
            "place_list_str": place_list_str,
            "people_list": people_list,
            "place_list": place_list,
            "min_distance_meters": min_distance_meters,
        })
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Get guidance lists failed: {str(e)}")


class NationIdRequest(BaseModel):
    nationid: str


class FinalKeyVerifyRequest(BaseModel):
    nationid: str
    final_key: str


def _sha256_hex(text_value: str) -> str:
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


def _generate_fragment(nationid: str, index: int) -> str:
    data = f"{SERVER_SECRET}{nationid}{index}"
    return _sha256_hex(data)[:6].upper()


def _expected_final_key(nationid: str) -> str:
    raw_key = "".join(
        [
            _generate_fragment(nationid, 1),
            _generate_fragment(nationid, 2),
            _generate_fragment(nationid, 3),
            _generate_fragment(nationid, 4),
        ]
    )
    return _sha256_hex(raw_key + nationid)

@app.get("/api/get_explore_tip_sf/")
async def get_explore_tip_sf():
    return {"success": True, "message": "Welcome to the New World.If you feel lost, visit the lady.Her torch illuminates the path,a guiding light for those who arrive in this new land."}

@app.get("/api/get_explore_tip_gw/")
async def get_explore_tip_gw():
    return {"success": True, "message": "Go to the Forbidden City,and claim the key hidden within its ancient halls."}


@app.post("/api/get_key_ny/")
async def get_key_ny(payload: NationIdRequest):
    if not payload.nationid:
        raise HTTPException(status_code=400, detail="nationid is required")
    return {"success": True, "data": {"k1": _generate_fragment(payload.nationid, 1),"message":"Stand where yesterday and tomorrow meet,and the path of the world will reveal itself.(Having gathered all four keys,you may journey to Singapore,seek the building, and claim the reward that awaits you.)"}}


@app.post("/api/get_key_ld/")
async def get_key_ld(payload: NationIdRequest):
    if not payload.nationid:
        raise HTTPException(status_code=400, detail="nationid is required")
    return {"success": True, "data": {"k2": _generate_fragment(payload.nationid, 2),"message":"Seek an audience with a lady,yet beware—do not lose yourself in her smile.She holds the secret that can make you the hero of yourself.(Having gathered all four keys,you may journey to Singapore,seek the building, and claim the reward that awaits you.)"}}


@app.post("/api/get_key_pr/")
async def get_key_pr(payload: NationIdRequest):
    if not payload.nationid:
        raise HTTPException(status_code=400, detail="nationid is required")
    return {"success": True, "data": {"k3": _generate_fragment(payload.nationid, 3),"message":"There is a place in the East.You must overcome every obstacle to reach it.You are not a true hero until you have been there.(Having gathered all four keys,you may journey to Singapore,seek the building, and claim the reward that awaits you.)"}}


@app.post("/api/get_key_pk/")
async def get_key_pk(payload: NationIdRequest):
    if not payload.nationid:
        raise HTTPException(status_code=400, detail="nationid is required")
    return {"success": True, "data": {"k4": _generate_fragment(payload.nationid, 4),"message":"In the 19th century, gold lured the brave there.In the 21st century, AI and data lure them again.Go there to find the treasure.(Having gathered all four keys,you may journey to Singapore,seek the building, and claim the reward that awaits you.)"}}


@app.post("/api/verify_final_key/")
async def verify_final_key(payload: FinalKeyVerifyRequest):
    if not payload.nationid:
        raise HTTPException(status_code=400, detail="nationid is required")
    if not payload.final_key:
        raise HTTPException(status_code=400, detail="final_key is required")

    nationid = payload.nationid
    raw_key_upper = "".join(
        [
            _generate_fragment(nationid, 1),
            _generate_fragment(nationid, 2),
            _generate_fragment(nationid, 3),
            _generate_fragment(nationid, 4),
        ]
    )
    expected_upper = _sha256_hex(raw_key_upper + nationid)
    expected_lower = _sha256_hex(raw_key_upper.lower() + nationid)

    provided_clean = (payload.final_key or "").strip()
    provided_lower = provided_clean.lower()
    provided_upper = provided_clean.upper()

    if not provided_clean or any(ch not in string.hexdigits for ch in provided_clean):
        raise HTTPException(status_code=400, detail="final_key must be hex")

    if len(provided_clean) == 24:
        valid = hmac.compare_digest(raw_key_upper, provided_upper) or hmac.compare_digest(raw_key_upper.lower(), provided_lower)
        return {"success": True, "data": {"valid": valid, "mode": "raw_key","reward":"AISNS_INT_SYSTEM_REWARD_START_1000000_AISNS_INT_SYSTEM_REWARD_END"}}

    if len(provided_clean) == 64:
        valid = hmac.compare_digest(expected_upper, provided_lower) or hmac.compare_digest(expected_lower, provided_lower)
        return {"success": True, "data": {"valid": valid, "mode": "final_key","reward":"AISNS_INT_SYSTEM_REWARD_START_1000000_AISNS_INT_SYSTEM_REWARD_END"}}

    raise HTTPException(status_code=400, detail="final_key length must be 24 (raw_key) or 64 (final_key)")


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
