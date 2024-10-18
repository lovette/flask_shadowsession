from flask.sessions import SecureCookieSessionInterface, SecureCookieSession, total_seconds
from flask_redisdict import RedisDict
from redis import StrictRedis


SHADOW_KEY_NAME = 'shadow_key'


class ShadowSessionDict(RedisDict):
    """Acts like a dictionary but reflects item access to Redis.

    Note:
        This is the actual ``shadow`` attribute of the global ``session``.

    Note:
        We only create the hash in Redis when the first key in the shadow session is accessed.
    """

    def __init__(self, *args, **kwargs):
        """Constructor"""
        super(ShadowSessionDict, self).__init__(*args, **kwargs)

        self.session = None
        self.accessed = False

    def open_session(self, session, redis, max_age):
        """Initialize shadow session.

        Arguments:
            max_age (int): Seconds

        Note:
            Called automatically on request setup.
        """
        assert isinstance(session, ShadowSession)
        assert isinstance(redis, StrictRedis)

        self.session = session
        self.accessed = False

        # RedisDict instance attributes
        self.redis = redis
        self.key = session.get(SHADOW_KEY_NAME, None)
        self.max_age = max_age

    def save_session(self, session):
        """Update session last access date and TTL.

        Note:
            Called automatically on request teardown.
        """

        if self.accessed is True and self.key is not None:
            p = self.redis.pipeline()
            self._on_save_session(p)
            if self.max_age is not None:
                p.expire(self.key, self.max_age)
            p.execute()

    def regenerate_key(self):
        """Generate a new hash key for this shadow session.

        Note:
            The session hash will not be changed. Only the key will be updated.

        Returns:
            string: New hash key
        """
        return self._create_hash()

    def _create_hash(self):
        """Override base class."""
        new_key = None
        reserve_key = None

        # Attempt to generate a new unique key
        for _ in xrange(100):
            possible_key = self._generate_key()
            reserve_key = possible_key + '-reserved'
            if self.redis.setnx(reserve_key, 1):
                if not self.redis.exists(possible_key):
                    new_key = possible_key
                    break
                self.redis.delete(reserve_key)
            else:
                # Someone else is trying to reserve this key!
                reserve_key = None

        if new_key is None:
            raise ValueError('Failed to generate unique shadow session key in 100 attempts.')

        p = self.redis.pipeline()

        if self.key is None:
            self.key = new_key
            self._on_create_hash(p)
        else:
            p.renamenx(self.key, new_key)
            self.key = new_key

        if self.max_age is not None:
            p.expire(self.key, self.max_age)
        if reserve_key is not None:
            p.delete(reserve_key)

        p.execute()

        # Carry around the shadow key in the session cookie
        self.session[SHADOW_KEY_NAME] = self.key

        return self.key

    def __getitem__(self, name):
        """Override base class."""
        self.accessed = True
        self.session.modified = True  # only applicable to permanent sessions
        return super(ShadowSessionDict, self).__getitem__(name)

    def __setitem__(self, name, value):
        """Override base class."""
        self.accessed = True
        self.session.modified = True  # only applicable to permanent sessions
        super(ShadowSessionDict, self).__setitem__(name, value)

    def __delitem__(self, name):
        """Override base class."""
        self.accessed = True
        self.session.modified = True  # only applicable to permanent sessions
        super(ShadowSessionDict, self).__delitem__(name)

    def exists(self):
        """Override base class."""
        rv = super(ShadowSessionDict, self).exists()
        if not rv and SHADOW_KEY_NAME in self.session:
            # Remove shadow key from the session cookie
            del self.session[SHADOW_KEY_NAME]
        return rv

    def delete(self):
        """Override base class."""
        super(ShadowSessionDict, self).delete()
        if SHADOW_KEY_NAME in self.session:
            # Remove shadow key from the session cookie
            del self.session[SHADOW_KEY_NAME]

    def _on_create_hash(self, p):
        """Update the hash as being created."""
        pass

    def _on_save_session(self, p):
        """Update the hash as session is saved."""
        pass


class ShadowSession(SecureCookieSession):
    """Session object that has a client-side ``SecureCookieSession`` and server-side "shadow" in Redis.

    Note:
        This is the actual globlal ``session`` object.
    """

    shadowdict_class = ShadowSessionDict

    # Force some fields that Flask normally stores in the session cookie to be saved in the shadow.
    _force_shadow_fields = frozenset((
        '_flashes',
        ))

    def __init__(self, *args, **kwargs):
        super(ShadowSession, self).__init__(*args, **kwargs)

        self.shadow = self.shadowdict_class()

    def __getitem__(self, name):
        """Override base class."""
        if name not in ShadowSession._force_shadow_fields:
            return super(ShadowSession, self).__getitem__(name)
        else:
            return self.shadow[name]

    def __setitem__(self, name, value):
        """Override base class."""
        if name not in ShadowSession._force_shadow_fields:
            super(ShadowSession, self).__setitem__(name, value)
        else:
            self.shadow[name] = value

    def __delitem__(self, name):
        """Override base class."""
        if name not in ShadowSession._force_shadow_fields:
            super(ShadowSession, self).__delitem__(name)
        else:
            del self.shadow[name]

    def __contains__(self, name):
        """Override base class."""
        if name not in ShadowSession._force_shadow_fields:
            return super(ShadowSession, self).__contains__(name)
        else:
            return self.shadow.__contains__(name)

    def pop(self, name, *args):
        """Override base class."""
        if name not in ShadowSession._force_shadow_fields:
            return super(ShadowSession, self).pop(name, *args)
        else:
            return self.shadow.pop(name, *args)


class ShadowSessionInterface(SecureCookieSessionInterface):
    """SessionInterface that has a client-side ``SecureCookieSession`` and server-side "shadow" in Redis."""

    # Have SecureCookieSessionInterface use our ShadowSession class
    session_class = ShadowSession

    redis = None
    """Class instance Redis connection. """

    def __init__(self, *args, **kwargs):
        super(ShadowSessionInterface, self).__init__(*args, **kwargs)

        self.max_age = None

    def open_session(self, app, request):
        """Override base class.

        Note:
            Called automatically on request setup.
        """
        session = super(ShadowSessionInterface, self).open_session(app, request)
        if session is None:
            return None

        # The browser will delete the session cookie when it closes. To prevent a cookie from being illegally saved
        # and replayed, our base class automatically encodes it with a max_age so it will not be honored
        # after the duration set in config['PERMANENT_SESSION_LIFETIME'].
        # This setting also defines the TTL of the the shadow session in Redis.
        session.permanent = False

        max_age = self.max_age or total_seconds(app.permanent_session_lifetime)

        session.shadow.open_session(session, self.redis, max_age)

        return session

    def save_session(self, app, session, response):
        """Override base class.

        Note:
            Called automatically on request teardown.
        """
        # Save default signed session cookie
        super(ShadowSessionInterface, self).save_session(app, session, response)

        # Update shadow session TTL
        session.shadow.save_session(session)
