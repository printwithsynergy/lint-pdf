
/**
 * Client
**/

import * as runtime from './runtime/client.js';
import $Types = runtime.Types // general types
import $Public = runtime.Types.Public
import $Utils = runtime.Types.Utils
import $Extensions = runtime.Types.Extensions
import $Result = runtime.Types.Result

export type PrismaPromise<T> = $Public.PrismaPromise<T>


/**
 * Model Tenant
 * 
 */
export type Tenant = $Result.DefaultSelection<Prisma.$TenantPayload>
/**
 * Model User
 * 
 */
export type User = $Result.DefaultSelection<Prisma.$UserPayload>
/**
 * Model TenantUser
 * 
 */
export type TenantUser = $Result.DefaultSelection<Prisma.$TenantUserPayload>
/**
 * Model TenantInvite
 * 
 */
export type TenantInvite = $Result.DefaultSelection<Prisma.$TenantInvitePayload>
/**
 * Model Session
 * 
 */
export type Session = $Result.DefaultSelection<Prisma.$SessionPayload>
/**
 * Model MagicLink
 * 
 */
export type MagicLink = $Result.DefaultSelection<Prisma.$MagicLinkPayload>
/**
 * Model AppSettings
 * 
 */
export type AppSettings = $Result.DefaultSelection<Prisma.$AppSettingsPayload>
/**
 * Model AuditLog
 * 
 */
export type AuditLog = $Result.DefaultSelection<Prisma.$AuditLogPayload>
/**
 * Model WaitlistEntry
 * 
 */
export type WaitlistEntry = $Result.DefaultSelection<Prisma.$WaitlistEntryPayload>
/**
 * Model Annotation
 * 
 */
export type Annotation = $Result.DefaultSelection<Prisma.$AnnotationPayload>
/**
 * Model ReportView
 * 
 */
export type ReportView = $Result.DefaultSelection<Prisma.$ReportViewPayload>

/**
 * Enums
 */
export namespace $Enums {
  export const TenantStatus: {
  ACTIVE: 'ACTIVE',
  ONBOARDING: 'ONBOARDING',
  SUSPENDED: 'SUSPENDED',
  ARCHIVED: 'ARCHIVED'
};

export type TenantStatus = (typeof TenantStatus)[keyof typeof TenantStatus]


export const TenantRole: {
  OWNER: 'OWNER',
  ADMIN: 'ADMIN',
  OPERATOR: 'OPERATOR',
  MEMBER: 'MEMBER',
  VIEWER: 'VIEWER'
};

export type TenantRole = (typeof TenantRole)[keyof typeof TenantRole]


export const WaitlistStatus: {
  PENDING: 'PENDING',
  PROMOTED: 'PROMOTED',
  DECLINED: 'DECLINED'
};

export type WaitlistStatus = (typeof WaitlistStatus)[keyof typeof WaitlistStatus]

}

export type TenantStatus = $Enums.TenantStatus

export const TenantStatus: typeof $Enums.TenantStatus

export type TenantRole = $Enums.TenantRole

export const TenantRole: typeof $Enums.TenantRole

export type WaitlistStatus = $Enums.WaitlistStatus

export const WaitlistStatus: typeof $Enums.WaitlistStatus

/**
 * ##  Prisma Client ʲˢ
 *
 * Type-safe database client for TypeScript & Node.js
 * @example
 * ```
 * const prisma = new PrismaClient({
 *   adapter: new PrismaPg({ connectionString: process.env.DATABASE_URL })
 * })
 * // Fetch zero or more Tenants
 * const tenants = await prisma.tenant.findMany()
 * ```
 *
 *
 * Read more in our [docs](https://pris.ly/d/client).
 */
export class PrismaClient<
  ClientOptions extends Prisma.PrismaClientOptions = Prisma.PrismaClientOptions,
  const U = 'log' extends keyof ClientOptions ? ClientOptions['log'] extends Array<Prisma.LogLevel | Prisma.LogDefinition> ? Prisma.GetEvents<ClientOptions['log']> : never : never,
  ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs
> {
  [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['other'] }

    /**
   * ##  Prisma Client ʲˢ
   *
   * Type-safe database client for TypeScript & Node.js
   * @example
   * ```
   * const prisma = new PrismaClient({
   *   adapter: new PrismaPg({ connectionString: process.env.DATABASE_URL })
   * })
   * // Fetch zero or more Tenants
   * const tenants = await prisma.tenant.findMany()
   * ```
   *
   *
   * Read more in our [docs](https://pris.ly/d/client).
   */

  constructor(optionsArg ?: Prisma.Subset<ClientOptions, Prisma.PrismaClientOptions>);
  $on<V extends U>(eventType: V, callback: (event: V extends 'query' ? Prisma.QueryEvent : Prisma.LogEvent) => void): PrismaClient;

  /**
   * Connect with the database
   */
  $connect(): $Utils.JsPromise<void>;

  /**
   * Disconnect from the database
   */
  $disconnect(): $Utils.JsPromise<void>;

/**
   * Executes a prepared raw query and returns the number of affected rows.
   * @example
   * ```
   * const result = await prisma.$executeRaw`UPDATE User SET cool = ${true} WHERE email = ${'user@email.com'};`
   * ```
   *
   * Read more in our [docs](https://pris.ly/d/raw-queries).
   */
  $executeRaw<T = unknown>(query: TemplateStringsArray | Prisma.Sql, ...values: any[]): Prisma.PrismaPromise<number>;

  /**
   * Executes a raw query and returns the number of affected rows.
   * Susceptible to SQL injections, see documentation.
   * @example
   * ```
   * const result = await prisma.$executeRawUnsafe('UPDATE User SET cool = $1 WHERE email = $2 ;', true, 'user@email.com')
   * ```
   *
   * Read more in our [docs](https://pris.ly/d/raw-queries).
   */
  $executeRawUnsafe<T = unknown>(query: string, ...values: any[]): Prisma.PrismaPromise<number>;

  /**
   * Performs a prepared raw query and returns the `SELECT` data.
   * @example
   * ```
   * const result = await prisma.$queryRaw`SELECT * FROM User WHERE id = ${1} OR email = ${'user@email.com'};`
   * ```
   *
   * Read more in our [docs](https://pris.ly/d/raw-queries).
   */
  $queryRaw<T = unknown>(query: TemplateStringsArray | Prisma.Sql, ...values: any[]): Prisma.PrismaPromise<T>;

  /**
   * Performs a raw query and returns the `SELECT` data.
   * Susceptible to SQL injections, see documentation.
   * @example
   * ```
   * const result = await prisma.$queryRawUnsafe('SELECT * FROM User WHERE id = $1 OR email = $2;', 1, 'user@email.com')
   * ```
   *
   * Read more in our [docs](https://pris.ly/d/raw-queries).
   */
  $queryRawUnsafe<T = unknown>(query: string, ...values: any[]): Prisma.PrismaPromise<T>;


  /**
   * Allows the running of a sequence of read/write operations that are guaranteed to either succeed or fail as a whole.
   * @example
   * ```
   * const [george, bob, alice] = await prisma.$transaction([
   *   prisma.user.create({ data: { name: 'George' } }),
   *   prisma.user.create({ data: { name: 'Bob' } }),
   *   prisma.user.create({ data: { name: 'Alice' } }),
   * ])
   * ```
   * 
   * Read more in our [docs](https://www.prisma.io/docs/orm/prisma-client/queries/transactions).
   */
  $transaction<P extends Prisma.PrismaPromise<any>[]>(arg: [...P], options?: { isolationLevel?: Prisma.TransactionIsolationLevel }): $Utils.JsPromise<runtime.Types.Utils.UnwrapTuple<P>>

  $transaction<R>(fn: (prisma: Omit<PrismaClient, runtime.ITXClientDenyList>) => $Utils.JsPromise<R>, options?: { maxWait?: number, timeout?: number, isolationLevel?: Prisma.TransactionIsolationLevel }): $Utils.JsPromise<R>

  $extends: $Extensions.ExtendsHook<"extends", Prisma.TypeMapCb<ClientOptions>, ExtArgs, $Utils.Call<Prisma.TypeMapCb<ClientOptions>, {
    extArgs: ExtArgs
  }>>

      /**
   * `prisma.tenant`: Exposes CRUD operations for the **Tenant** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Tenants
    * const tenants = await prisma.tenant.findMany()
    * ```
    */
  get tenant(): Prisma.TenantDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.user`: Exposes CRUD operations for the **User** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Users
    * const users = await prisma.user.findMany()
    * ```
    */
  get user(): Prisma.UserDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.tenantUser`: Exposes CRUD operations for the **TenantUser** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more TenantUsers
    * const tenantUsers = await prisma.tenantUser.findMany()
    * ```
    */
  get tenantUser(): Prisma.TenantUserDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.tenantInvite`: Exposes CRUD operations for the **TenantInvite** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more TenantInvites
    * const tenantInvites = await prisma.tenantInvite.findMany()
    * ```
    */
  get tenantInvite(): Prisma.TenantInviteDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.session`: Exposes CRUD operations for the **Session** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Sessions
    * const sessions = await prisma.session.findMany()
    * ```
    */
  get session(): Prisma.SessionDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.magicLink`: Exposes CRUD operations for the **MagicLink** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more MagicLinks
    * const magicLinks = await prisma.magicLink.findMany()
    * ```
    */
  get magicLink(): Prisma.MagicLinkDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.appSettings`: Exposes CRUD operations for the **AppSettings** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more AppSettings
    * const appSettings = await prisma.appSettings.findMany()
    * ```
    */
  get appSettings(): Prisma.AppSettingsDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.auditLog`: Exposes CRUD operations for the **AuditLog** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more AuditLogs
    * const auditLogs = await prisma.auditLog.findMany()
    * ```
    */
  get auditLog(): Prisma.AuditLogDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.waitlistEntry`: Exposes CRUD operations for the **WaitlistEntry** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more WaitlistEntries
    * const waitlistEntries = await prisma.waitlistEntry.findMany()
    * ```
    */
  get waitlistEntry(): Prisma.WaitlistEntryDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.annotation`: Exposes CRUD operations for the **Annotation** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Annotations
    * const annotations = await prisma.annotation.findMany()
    * ```
    */
  get annotation(): Prisma.AnnotationDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.reportView`: Exposes CRUD operations for the **ReportView** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more ReportViews
    * const reportViews = await prisma.reportView.findMany()
    * ```
    */
  get reportView(): Prisma.ReportViewDelegate<ExtArgs, ClientOptions>;
}

export namespace Prisma {
  export import DMMF = runtime.DMMF

  export type PrismaPromise<T> = $Public.PrismaPromise<T>

  /**
   * Validator
   */
  export import validator = runtime.Public.validator

  /**
   * Prisma Errors
   */
  export import PrismaClientKnownRequestError = runtime.PrismaClientKnownRequestError
  export import PrismaClientUnknownRequestError = runtime.PrismaClientUnknownRequestError
  export import PrismaClientRustPanicError = runtime.PrismaClientRustPanicError
  export import PrismaClientInitializationError = runtime.PrismaClientInitializationError
  export import PrismaClientValidationError = runtime.PrismaClientValidationError

  /**
   * Re-export of sql-template-tag
   */
  export import sql = runtime.sqltag
  export import empty = runtime.empty
  export import join = runtime.join
  export import raw = runtime.raw
  export import Sql = runtime.Sql



  /**
   * Decimal.js
   */
  export import Decimal = runtime.Decimal

  export type DecimalJsLike = runtime.DecimalJsLike

  /**
  * Extensions
  */
  export import Extension = $Extensions.UserArgs
  export import getExtensionContext = runtime.Extensions.getExtensionContext
  export import Args = $Public.Args
  export import Payload = $Public.Payload
  export import Result = $Public.Result
  export import Exact = $Public.Exact

  /**
   * Prisma Client JS version: 7.6.0
   * Query Engine version: 75cbdc1eb7150937890ad5465d861175c6624711
   */
  export type PrismaVersion = {
    client: string
    engine: string
  }

  export const prismaVersion: PrismaVersion

  /**
   * Utility Types
   */


  export import Bytes = runtime.Bytes
  export import JsonObject = runtime.JsonObject
  export import JsonArray = runtime.JsonArray
  export import JsonValue = runtime.JsonValue
  export import InputJsonObject = runtime.InputJsonObject
  export import InputJsonArray = runtime.InputJsonArray
  export import InputJsonValue = runtime.InputJsonValue

  /**
   * Types of the values used to represent different kinds of `null` values when working with JSON fields.
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  namespace NullTypes {
    /**
    * Type of `Prisma.DbNull`.
    *
    * You cannot use other instances of this class. Please use the `Prisma.DbNull` value.
    *
    * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
    */
    class DbNull {
      private DbNull: never
      private constructor()
    }

    /**
    * Type of `Prisma.JsonNull`.
    *
    * You cannot use other instances of this class. Please use the `Prisma.JsonNull` value.
    *
    * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
    */
    class JsonNull {
      private JsonNull: never
      private constructor()
    }

    /**
    * Type of `Prisma.AnyNull`.
    *
    * You cannot use other instances of this class. Please use the `Prisma.AnyNull` value.
    *
    * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
    */
    class AnyNull {
      private AnyNull: never
      private constructor()
    }
  }

  /**
   * Helper for filtering JSON entries that have `null` on the database (empty on the db)
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  export const DbNull: NullTypes.DbNull

  /**
   * Helper for filtering JSON entries that have JSON `null` values (not empty on the db)
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  export const JsonNull: NullTypes.JsonNull

  /**
   * Helper for filtering JSON entries that are `Prisma.DbNull` or `Prisma.JsonNull`
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  export const AnyNull: NullTypes.AnyNull

  type SelectAndInclude = {
    select: any
    include: any
  }

  type SelectAndOmit = {
    select: any
    omit: any
  }

  /**
   * Get the type of the value, that the Promise holds.
   */
  export type PromiseType<T extends PromiseLike<any>> = T extends PromiseLike<infer U> ? U : T;

  /**
   * Get the return type of a function which returns a Promise.
   */
  export type PromiseReturnType<T extends (...args: any) => $Utils.JsPromise<any>> = PromiseType<ReturnType<T>>

  /**
   * From T, pick a set of properties whose keys are in the union K
   */
  type Prisma__Pick<T, K extends keyof T> = {
      [P in K]: T[P];
  };


  export type Enumerable<T> = T | Array<T>;

  export type RequiredKeys<T> = {
    [K in keyof T]-?: {} extends Prisma__Pick<T, K> ? never : K
  }[keyof T]

  export type TruthyKeys<T> = keyof {
    [K in keyof T as T[K] extends false | undefined | null ? never : K]: K
  }

  export type TrueKeys<T> = TruthyKeys<Prisma__Pick<T, RequiredKeys<T>>>

  /**
   * Subset
   * @desc From `T` pick properties that exist in `U`. Simple version of Intersection
   */
  export type Subset<T, U> = {
    [key in keyof T]: key extends keyof U ? T[key] : never;
  };

  /**
   * SelectSubset
   * @desc From `T` pick properties that exist in `U`. Simple version of Intersection.
   * Additionally, it validates, if both select and include are present. If the case, it errors.
   */
  export type SelectSubset<T, U> = {
    [key in keyof T]: key extends keyof U ? T[key] : never
  } &
    (T extends SelectAndInclude
      ? 'Please either choose `select` or `include`.'
      : T extends SelectAndOmit
        ? 'Please either choose `select` or `omit`.'
        : {})

  /**
   * Subset + Intersection
   * @desc From `T` pick properties that exist in `U` and intersect `K`
   */
  export type SubsetIntersection<T, U, K> = {
    [key in keyof T]: key extends keyof U ? T[key] : never
  } &
    K

  type Without<T, U> = { [P in Exclude<keyof T, keyof U>]?: never };

  /**
   * XOR is needed to have a real mutually exclusive union type
   * https://stackoverflow.com/questions/42123407/does-typescript-support-mutually-exclusive-types
   */
  type XOR<T, U> =
    T extends object ?
    U extends object ?
      (Without<T, U> & U) | (Without<U, T> & T)
    : U : T


  /**
   * Is T a Record?
   */
  type IsObject<T extends any> = T extends Array<any>
  ? False
  : T extends Date
  ? False
  : T extends Uint8Array
  ? False
  : T extends BigInt
  ? False
  : T extends object
  ? True
  : False


  /**
   * If it's T[], return T
   */
  export type UnEnumerate<T extends unknown> = T extends Array<infer U> ? U : T

  /**
   * From ts-toolbelt
   */

  type __Either<O extends object, K extends Key> = Omit<O, K> &
    {
      // Merge all but K
      [P in K]: Prisma__Pick<O, P & keyof O> // With K possibilities
    }[K]

  type EitherStrict<O extends object, K extends Key> = Strict<__Either<O, K>>

  type EitherLoose<O extends object, K extends Key> = ComputeRaw<__Either<O, K>>

  type _Either<
    O extends object,
    K extends Key,
    strict extends Boolean
  > = {
    1: EitherStrict<O, K>
    0: EitherLoose<O, K>
  }[strict]

  type Either<
    O extends object,
    K extends Key,
    strict extends Boolean = 1
  > = O extends unknown ? _Either<O, K, strict> : never

  export type Union = any

  type PatchUndefined<O extends object, O1 extends object> = {
    [K in keyof O]: O[K] extends undefined ? At<O1, K> : O[K]
  } & {}

  /** Helper Types for "Merge" **/
  export type IntersectOf<U extends Union> = (
    U extends unknown ? (k: U) => void : never
  ) extends (k: infer I) => void
    ? I
    : never

  export type Overwrite<O extends object, O1 extends object> = {
      [K in keyof O]: K extends keyof O1 ? O1[K] : O[K];
  } & {};

  type _Merge<U extends object> = IntersectOf<Overwrite<U, {
      [K in keyof U]-?: At<U, K>;
  }>>;

  type Key = string | number | symbol;
  type AtBasic<O extends object, K extends Key> = K extends keyof O ? O[K] : never;
  type AtStrict<O extends object, K extends Key> = O[K & keyof O];
  type AtLoose<O extends object, K extends Key> = O extends unknown ? AtStrict<O, K> : never;
  export type At<O extends object, K extends Key, strict extends Boolean = 1> = {
      1: AtStrict<O, K>;
      0: AtLoose<O, K>;
  }[strict];

  export type ComputeRaw<A extends any> = A extends Function ? A : {
    [K in keyof A]: A[K];
  } & {};

  export type OptionalFlat<O> = {
    [K in keyof O]?: O[K];
  } & {};

  type _Record<K extends keyof any, T> = {
    [P in K]: T;
  };

  // cause typescript not to expand types and preserve names
  type NoExpand<T> = T extends unknown ? T : never;

  // this type assumes the passed object is entirely optional
  type AtLeast<O extends object, K extends string> = NoExpand<
    O extends unknown
    ? | (K extends keyof O ? { [P in K]: O[P] } & O : O)
      | {[P in keyof O as P extends K ? P : never]-?: O[P]} & O
    : never>;

  type _Strict<U, _U = U> = U extends unknown ? U & OptionalFlat<_Record<Exclude<Keys<_U>, keyof U>, never>> : never;

  export type Strict<U extends object> = ComputeRaw<_Strict<U>>;
  /** End Helper Types for "Merge" **/

  export type Merge<U extends object> = ComputeRaw<_Merge<Strict<U>>>;

  /**
  A [[Boolean]]
  */
  export type Boolean = True | False

  // /**
  // 1
  // */
  export type True = 1

  /**
  0
  */
  export type False = 0

  export type Not<B extends Boolean> = {
    0: 1
    1: 0
  }[B]

  export type Extends<A1 extends any, A2 extends any> = [A1] extends [never]
    ? 0 // anything `never` is false
    : A1 extends A2
    ? 1
    : 0

  export type Has<U extends Union, U1 extends Union> = Not<
    Extends<Exclude<U1, U>, U1>
  >

  export type Or<B1 extends Boolean, B2 extends Boolean> = {
    0: {
      0: 0
      1: 1
    }
    1: {
      0: 1
      1: 1
    }
  }[B1][B2]

  export type Keys<U extends Union> = U extends unknown ? keyof U : never

  type Cast<A, B> = A extends B ? A : B;

  export const type: unique symbol;



  /**
   * Used by group by
   */

  export type GetScalarType<T, O> = O extends object ? {
    [P in keyof T]: P extends keyof O
      ? O[P]
      : never
  } : never

  type FieldPaths<
    T,
    U = Omit<T, '_avg' | '_sum' | '_count' | '_min' | '_max'>
  > = IsObject<T> extends True ? U : T

  type GetHavingFields<T> = {
    [K in keyof T]: Or<
      Or<Extends<'OR', K>, Extends<'AND', K>>,
      Extends<'NOT', K>
    > extends True
      ? // infer is only needed to not hit TS limit
        // based on the brilliant idea of Pierre-Antoine Mills
        // https://github.com/microsoft/TypeScript/issues/30188#issuecomment-478938437
        T[K] extends infer TK
        ? GetHavingFields<UnEnumerate<TK> extends object ? Merge<UnEnumerate<TK>> : never>
        : never
      : {} extends FieldPaths<T[K]>
      ? never
      : K
  }[keyof T]

  /**
   * Convert tuple to union
   */
  type _TupleToUnion<T> = T extends (infer E)[] ? E : never
  type TupleToUnion<K extends readonly any[]> = _TupleToUnion<K>
  type MaybeTupleToUnion<T> = T extends any[] ? TupleToUnion<T> : T

  /**
   * Like `Pick`, but additionally can also accept an array of keys
   */
  type PickEnumerable<T, K extends Enumerable<keyof T> | keyof T> = Prisma__Pick<T, MaybeTupleToUnion<K>>

  /**
   * Exclude all keys with underscores
   */
  type ExcludeUnderscoreKeys<T extends string> = T extends `_${string}` ? never : T


  export type FieldRef<Model, FieldType> = runtime.FieldRef<Model, FieldType>

  type FieldRefInputType<Model, FieldType> = Model extends never ? never : FieldRef<Model, FieldType>


  export const ModelName: {
    Tenant: 'Tenant',
    User: 'User',
    TenantUser: 'TenantUser',
    TenantInvite: 'TenantInvite',
    Session: 'Session',
    MagicLink: 'MagicLink',
    AppSettings: 'AppSettings',
    AuditLog: 'AuditLog',
    WaitlistEntry: 'WaitlistEntry',
    Annotation: 'Annotation',
    ReportView: 'ReportView'
  };

  export type ModelName = (typeof ModelName)[keyof typeof ModelName]



  interface TypeMapCb<ClientOptions = {}> extends $Utils.Fn<{extArgs: $Extensions.InternalArgs }, $Utils.Record<string, any>> {
    returns: Prisma.TypeMap<this['params']['extArgs'], ClientOptions extends { omit: infer OmitOptions } ? OmitOptions : {}>
  }

  export type TypeMap<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> = {
    globalOmitOptions: {
      omit: GlobalOmitOptions
    }
    meta: {
      modelProps: "tenant" | "user" | "tenantUser" | "tenantInvite" | "session" | "magicLink" | "appSettings" | "auditLog" | "waitlistEntry" | "annotation" | "reportView"
      txIsolationLevel: Prisma.TransactionIsolationLevel
    }
    model: {
      Tenant: {
        payload: Prisma.$TenantPayload<ExtArgs>
        fields: Prisma.TenantFieldRefs
        operations: {
          findUnique: {
            args: Prisma.TenantFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.TenantFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload>
          }
          findFirst: {
            args: Prisma.TenantFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.TenantFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload>
          }
          findMany: {
            args: Prisma.TenantFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload>[]
          }
          create: {
            args: Prisma.TenantCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload>
          }
          createMany: {
            args: Prisma.TenantCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.TenantCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload>[]
          }
          delete: {
            args: Prisma.TenantDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload>
          }
          update: {
            args: Prisma.TenantUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload>
          }
          deleteMany: {
            args: Prisma.TenantDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.TenantUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.TenantUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload>[]
          }
          upsert: {
            args: Prisma.TenantUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantPayload>
          }
          aggregate: {
            args: Prisma.TenantAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateTenant>
          }
          groupBy: {
            args: Prisma.TenantGroupByArgs<ExtArgs>
            result: $Utils.Optional<TenantGroupByOutputType>[]
          }
          count: {
            args: Prisma.TenantCountArgs<ExtArgs>
            result: $Utils.Optional<TenantCountAggregateOutputType> | number
          }
        }
      }
      User: {
        payload: Prisma.$UserPayload<ExtArgs>
        fields: Prisma.UserFieldRefs
        operations: {
          findUnique: {
            args: Prisma.UserFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.UserFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          findFirst: {
            args: Prisma.UserFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.UserFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          findMany: {
            args: Prisma.UserFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>[]
          }
          create: {
            args: Prisma.UserCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          createMany: {
            args: Prisma.UserCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.UserCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>[]
          }
          delete: {
            args: Prisma.UserDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          update: {
            args: Prisma.UserUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          deleteMany: {
            args: Prisma.UserDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.UserUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.UserUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>[]
          }
          upsert: {
            args: Prisma.UserUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          aggregate: {
            args: Prisma.UserAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateUser>
          }
          groupBy: {
            args: Prisma.UserGroupByArgs<ExtArgs>
            result: $Utils.Optional<UserGroupByOutputType>[]
          }
          count: {
            args: Prisma.UserCountArgs<ExtArgs>
            result: $Utils.Optional<UserCountAggregateOutputType> | number
          }
        }
      }
      TenantUser: {
        payload: Prisma.$TenantUserPayload<ExtArgs>
        fields: Prisma.TenantUserFieldRefs
        operations: {
          findUnique: {
            args: Prisma.TenantUserFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.TenantUserFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload>
          }
          findFirst: {
            args: Prisma.TenantUserFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.TenantUserFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload>
          }
          findMany: {
            args: Prisma.TenantUserFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload>[]
          }
          create: {
            args: Prisma.TenantUserCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload>
          }
          createMany: {
            args: Prisma.TenantUserCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.TenantUserCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload>[]
          }
          delete: {
            args: Prisma.TenantUserDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload>
          }
          update: {
            args: Prisma.TenantUserUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload>
          }
          deleteMany: {
            args: Prisma.TenantUserDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.TenantUserUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.TenantUserUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload>[]
          }
          upsert: {
            args: Prisma.TenantUserUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantUserPayload>
          }
          aggregate: {
            args: Prisma.TenantUserAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateTenantUser>
          }
          groupBy: {
            args: Prisma.TenantUserGroupByArgs<ExtArgs>
            result: $Utils.Optional<TenantUserGroupByOutputType>[]
          }
          count: {
            args: Prisma.TenantUserCountArgs<ExtArgs>
            result: $Utils.Optional<TenantUserCountAggregateOutputType> | number
          }
        }
      }
      TenantInvite: {
        payload: Prisma.$TenantInvitePayload<ExtArgs>
        fields: Prisma.TenantInviteFieldRefs
        operations: {
          findUnique: {
            args: Prisma.TenantInviteFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.TenantInviteFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload>
          }
          findFirst: {
            args: Prisma.TenantInviteFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.TenantInviteFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload>
          }
          findMany: {
            args: Prisma.TenantInviteFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload>[]
          }
          create: {
            args: Prisma.TenantInviteCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload>
          }
          createMany: {
            args: Prisma.TenantInviteCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.TenantInviteCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload>[]
          }
          delete: {
            args: Prisma.TenantInviteDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload>
          }
          update: {
            args: Prisma.TenantInviteUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload>
          }
          deleteMany: {
            args: Prisma.TenantInviteDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.TenantInviteUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.TenantInviteUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload>[]
          }
          upsert: {
            args: Prisma.TenantInviteUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TenantInvitePayload>
          }
          aggregate: {
            args: Prisma.TenantInviteAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateTenantInvite>
          }
          groupBy: {
            args: Prisma.TenantInviteGroupByArgs<ExtArgs>
            result: $Utils.Optional<TenantInviteGroupByOutputType>[]
          }
          count: {
            args: Prisma.TenantInviteCountArgs<ExtArgs>
            result: $Utils.Optional<TenantInviteCountAggregateOutputType> | number
          }
        }
      }
      Session: {
        payload: Prisma.$SessionPayload<ExtArgs>
        fields: Prisma.SessionFieldRefs
        operations: {
          findUnique: {
            args: Prisma.SessionFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.SessionFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          findFirst: {
            args: Prisma.SessionFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.SessionFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          findMany: {
            args: Prisma.SessionFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>[]
          }
          create: {
            args: Prisma.SessionCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          createMany: {
            args: Prisma.SessionCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.SessionCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>[]
          }
          delete: {
            args: Prisma.SessionDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          update: {
            args: Prisma.SessionUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          deleteMany: {
            args: Prisma.SessionDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.SessionUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.SessionUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>[]
          }
          upsert: {
            args: Prisma.SessionUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          aggregate: {
            args: Prisma.SessionAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateSession>
          }
          groupBy: {
            args: Prisma.SessionGroupByArgs<ExtArgs>
            result: $Utils.Optional<SessionGroupByOutputType>[]
          }
          count: {
            args: Prisma.SessionCountArgs<ExtArgs>
            result: $Utils.Optional<SessionCountAggregateOutputType> | number
          }
        }
      }
      MagicLink: {
        payload: Prisma.$MagicLinkPayload<ExtArgs>
        fields: Prisma.MagicLinkFieldRefs
        operations: {
          findUnique: {
            args: Prisma.MagicLinkFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.MagicLinkFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload>
          }
          findFirst: {
            args: Prisma.MagicLinkFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.MagicLinkFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload>
          }
          findMany: {
            args: Prisma.MagicLinkFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload>[]
          }
          create: {
            args: Prisma.MagicLinkCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload>
          }
          createMany: {
            args: Prisma.MagicLinkCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.MagicLinkCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload>[]
          }
          delete: {
            args: Prisma.MagicLinkDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload>
          }
          update: {
            args: Prisma.MagicLinkUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload>
          }
          deleteMany: {
            args: Prisma.MagicLinkDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.MagicLinkUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.MagicLinkUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload>[]
          }
          upsert: {
            args: Prisma.MagicLinkUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MagicLinkPayload>
          }
          aggregate: {
            args: Prisma.MagicLinkAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateMagicLink>
          }
          groupBy: {
            args: Prisma.MagicLinkGroupByArgs<ExtArgs>
            result: $Utils.Optional<MagicLinkGroupByOutputType>[]
          }
          count: {
            args: Prisma.MagicLinkCountArgs<ExtArgs>
            result: $Utils.Optional<MagicLinkCountAggregateOutputType> | number
          }
        }
      }
      AppSettings: {
        payload: Prisma.$AppSettingsPayload<ExtArgs>
        fields: Prisma.AppSettingsFieldRefs
        operations: {
          findUnique: {
            args: Prisma.AppSettingsFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.AppSettingsFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload>
          }
          findFirst: {
            args: Prisma.AppSettingsFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.AppSettingsFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload>
          }
          findMany: {
            args: Prisma.AppSettingsFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload>[]
          }
          create: {
            args: Prisma.AppSettingsCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload>
          }
          createMany: {
            args: Prisma.AppSettingsCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.AppSettingsCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload>[]
          }
          delete: {
            args: Prisma.AppSettingsDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload>
          }
          update: {
            args: Prisma.AppSettingsUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload>
          }
          deleteMany: {
            args: Prisma.AppSettingsDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.AppSettingsUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.AppSettingsUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload>[]
          }
          upsert: {
            args: Prisma.AppSettingsUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AppSettingsPayload>
          }
          aggregate: {
            args: Prisma.AppSettingsAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateAppSettings>
          }
          groupBy: {
            args: Prisma.AppSettingsGroupByArgs<ExtArgs>
            result: $Utils.Optional<AppSettingsGroupByOutputType>[]
          }
          count: {
            args: Prisma.AppSettingsCountArgs<ExtArgs>
            result: $Utils.Optional<AppSettingsCountAggregateOutputType> | number
          }
        }
      }
      AuditLog: {
        payload: Prisma.$AuditLogPayload<ExtArgs>
        fields: Prisma.AuditLogFieldRefs
        operations: {
          findUnique: {
            args: Prisma.AuditLogFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.AuditLogFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          findFirst: {
            args: Prisma.AuditLogFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.AuditLogFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          findMany: {
            args: Prisma.AuditLogFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>[]
          }
          create: {
            args: Prisma.AuditLogCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          createMany: {
            args: Prisma.AuditLogCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.AuditLogCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>[]
          }
          delete: {
            args: Prisma.AuditLogDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          update: {
            args: Prisma.AuditLogUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          deleteMany: {
            args: Prisma.AuditLogDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.AuditLogUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.AuditLogUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>[]
          }
          upsert: {
            args: Prisma.AuditLogUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          aggregate: {
            args: Prisma.AuditLogAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateAuditLog>
          }
          groupBy: {
            args: Prisma.AuditLogGroupByArgs<ExtArgs>
            result: $Utils.Optional<AuditLogGroupByOutputType>[]
          }
          count: {
            args: Prisma.AuditLogCountArgs<ExtArgs>
            result: $Utils.Optional<AuditLogCountAggregateOutputType> | number
          }
        }
      }
      WaitlistEntry: {
        payload: Prisma.$WaitlistEntryPayload<ExtArgs>
        fields: Prisma.WaitlistEntryFieldRefs
        operations: {
          findUnique: {
            args: Prisma.WaitlistEntryFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.WaitlistEntryFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload>
          }
          findFirst: {
            args: Prisma.WaitlistEntryFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.WaitlistEntryFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload>
          }
          findMany: {
            args: Prisma.WaitlistEntryFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload>[]
          }
          create: {
            args: Prisma.WaitlistEntryCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload>
          }
          createMany: {
            args: Prisma.WaitlistEntryCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.WaitlistEntryCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload>[]
          }
          delete: {
            args: Prisma.WaitlistEntryDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload>
          }
          update: {
            args: Prisma.WaitlistEntryUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload>
          }
          deleteMany: {
            args: Prisma.WaitlistEntryDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.WaitlistEntryUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.WaitlistEntryUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload>[]
          }
          upsert: {
            args: Prisma.WaitlistEntryUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WaitlistEntryPayload>
          }
          aggregate: {
            args: Prisma.WaitlistEntryAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateWaitlistEntry>
          }
          groupBy: {
            args: Prisma.WaitlistEntryGroupByArgs<ExtArgs>
            result: $Utils.Optional<WaitlistEntryGroupByOutputType>[]
          }
          count: {
            args: Prisma.WaitlistEntryCountArgs<ExtArgs>
            result: $Utils.Optional<WaitlistEntryCountAggregateOutputType> | number
          }
        }
      }
      Annotation: {
        payload: Prisma.$AnnotationPayload<ExtArgs>
        fields: Prisma.AnnotationFieldRefs
        operations: {
          findUnique: {
            args: Prisma.AnnotationFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.AnnotationFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload>
          }
          findFirst: {
            args: Prisma.AnnotationFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.AnnotationFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload>
          }
          findMany: {
            args: Prisma.AnnotationFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload>[]
          }
          create: {
            args: Prisma.AnnotationCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload>
          }
          createMany: {
            args: Prisma.AnnotationCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.AnnotationCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload>[]
          }
          delete: {
            args: Prisma.AnnotationDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload>
          }
          update: {
            args: Prisma.AnnotationUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload>
          }
          deleteMany: {
            args: Prisma.AnnotationDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.AnnotationUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.AnnotationUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload>[]
          }
          upsert: {
            args: Prisma.AnnotationUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AnnotationPayload>
          }
          aggregate: {
            args: Prisma.AnnotationAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateAnnotation>
          }
          groupBy: {
            args: Prisma.AnnotationGroupByArgs<ExtArgs>
            result: $Utils.Optional<AnnotationGroupByOutputType>[]
          }
          count: {
            args: Prisma.AnnotationCountArgs<ExtArgs>
            result: $Utils.Optional<AnnotationCountAggregateOutputType> | number
          }
        }
      }
      ReportView: {
        payload: Prisma.$ReportViewPayload<ExtArgs>
        fields: Prisma.ReportViewFieldRefs
        operations: {
          findUnique: {
            args: Prisma.ReportViewFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.ReportViewFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload>
          }
          findFirst: {
            args: Prisma.ReportViewFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.ReportViewFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload>
          }
          findMany: {
            args: Prisma.ReportViewFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload>[]
          }
          create: {
            args: Prisma.ReportViewCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload>
          }
          createMany: {
            args: Prisma.ReportViewCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.ReportViewCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload>[]
          }
          delete: {
            args: Prisma.ReportViewDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload>
          }
          update: {
            args: Prisma.ReportViewUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload>
          }
          deleteMany: {
            args: Prisma.ReportViewDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.ReportViewUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.ReportViewUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload>[]
          }
          upsert: {
            args: Prisma.ReportViewUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ReportViewPayload>
          }
          aggregate: {
            args: Prisma.ReportViewAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateReportView>
          }
          groupBy: {
            args: Prisma.ReportViewGroupByArgs<ExtArgs>
            result: $Utils.Optional<ReportViewGroupByOutputType>[]
          }
          count: {
            args: Prisma.ReportViewCountArgs<ExtArgs>
            result: $Utils.Optional<ReportViewCountAggregateOutputType> | number
          }
        }
      }
    }
  } & {
    other: {
      payload: any
      operations: {
        $executeRaw: {
          args: [query: TemplateStringsArray | Prisma.Sql, ...values: any[]],
          result: any
        }
        $executeRawUnsafe: {
          args: [query: string, ...values: any[]],
          result: any
        }
        $queryRaw: {
          args: [query: TemplateStringsArray | Prisma.Sql, ...values: any[]],
          result: any
        }
        $queryRawUnsafe: {
          args: [query: string, ...values: any[]],
          result: any
        }
      }
    }
  }
  export const defineExtension: $Extensions.ExtendsHook<"define", Prisma.TypeMapCb, $Extensions.DefaultArgs>
  export type DefaultPrismaClient = PrismaClient
  export type ErrorFormat = 'pretty' | 'colorless' | 'minimal'
  export interface PrismaClientOptions {
    /**
     * @default "colorless"
     */
    errorFormat?: ErrorFormat
    /**
     * @example
     * ```
     * // Shorthand for `emit: 'stdout'`
     * log: ['query', 'info', 'warn', 'error']
     * 
     * // Emit as events only
     * log: [
     *   { emit: 'event', level: 'query' },
     *   { emit: 'event', level: 'info' },
     *   { emit: 'event', level: 'warn' }
     *   { emit: 'event', level: 'error' }
     * ]
     * 
     * / Emit as events and log to stdout
     * og: [
     *  { emit: 'stdout', level: 'query' },
     *  { emit: 'stdout', level: 'info' },
     *  { emit: 'stdout', level: 'warn' }
     *  { emit: 'stdout', level: 'error' }
     * 
     * ```
     * Read more in our [docs](https://pris.ly/d/logging).
     */
    log?: (LogLevel | LogDefinition)[]
    /**
     * The default values for transactionOptions
     * maxWait ?= 2000
     * timeout ?= 5000
     */
    transactionOptions?: {
      maxWait?: number
      timeout?: number
      isolationLevel?: Prisma.TransactionIsolationLevel
    }
    /**
     * Instance of a Driver Adapter, e.g., like one provided by `@prisma/adapter-planetscale`
     */
    adapter?: runtime.SqlDriverAdapterFactory
    /**
     * Prisma Accelerate URL allowing the client to connect through Accelerate instead of a direct database.
     */
    accelerateUrl?: string
    /**
     * Global configuration for omitting model fields by default.
     * 
     * @example
     * ```
     * const prisma = new PrismaClient({
     *   omit: {
     *     user: {
     *       password: true
     *     }
     *   }
     * })
     * ```
     */
    omit?: Prisma.GlobalOmitConfig
    /**
     * SQL commenter plugins that add metadata to SQL queries as comments.
     * Comments follow the sqlcommenter format: https://google.github.io/sqlcommenter/
     * 
     * @example
     * ```
     * const prisma = new PrismaClient({
     *   adapter,
     *   comments: [
     *     traceContext(),
     *     queryInsights(),
     *   ],
     * })
     * ```
     */
    comments?: runtime.SqlCommenterPlugin[]
  }
  export type GlobalOmitConfig = {
    tenant?: TenantOmit
    user?: UserOmit
    tenantUser?: TenantUserOmit
    tenantInvite?: TenantInviteOmit
    session?: SessionOmit
    magicLink?: MagicLinkOmit
    appSettings?: AppSettingsOmit
    auditLog?: AuditLogOmit
    waitlistEntry?: WaitlistEntryOmit
    annotation?: AnnotationOmit
    reportView?: ReportViewOmit
  }

  /* Types for Logging */
  export type LogLevel = 'info' | 'query' | 'warn' | 'error'
  export type LogDefinition = {
    level: LogLevel
    emit: 'stdout' | 'event'
  }

  export type CheckIsLogLevel<T> = T extends LogLevel ? T : never;

  export type GetLogType<T> = CheckIsLogLevel<
    T extends LogDefinition ? T['level'] : T
  >;

  export type GetEvents<T extends any[]> = T extends Array<LogLevel | LogDefinition>
    ? GetLogType<T[number]>
    : never;

  export type QueryEvent = {
    timestamp: Date
    query: string
    params: string
    duration: number
    target: string
  }

  export type LogEvent = {
    timestamp: Date
    message: string
    target: string
  }
  /* End Types for Logging */


  export type PrismaAction =
    | 'findUnique'
    | 'findUniqueOrThrow'
    | 'findMany'
    | 'findFirst'
    | 'findFirstOrThrow'
    | 'create'
    | 'createMany'
    | 'createManyAndReturn'
    | 'update'
    | 'updateMany'
    | 'updateManyAndReturn'
    | 'upsert'
    | 'delete'
    | 'deleteMany'
    | 'executeRaw'
    | 'queryRaw'
    | 'aggregate'
    | 'count'
    | 'runCommandRaw'
    | 'findRaw'
    | 'groupBy'

  // tested in getLogLevel.test.ts
  export function getLogLevel(log: Array<LogLevel | LogDefinition>): LogLevel | undefined;

  /**
   * `PrismaClient` proxy available in interactive transactions.
   */
  export type TransactionClient = Omit<Prisma.DefaultPrismaClient, runtime.ITXClientDenyList>

  export type Datasource = {
    url?: string
  }

  /**
   * Count Types
   */


  /**
   * Count Type TenantCountOutputType
   */

  export type TenantCountOutputType = {
    users: number
    invites: number
    annotations: number
    reportViews: number
  }

  export type TenantCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    users?: boolean | TenantCountOutputTypeCountUsersArgs
    invites?: boolean | TenantCountOutputTypeCountInvitesArgs
    annotations?: boolean | TenantCountOutputTypeCountAnnotationsArgs
    reportViews?: boolean | TenantCountOutputTypeCountReportViewsArgs
  }

  // Custom InputTypes
  /**
   * TenantCountOutputType without action
   */
  export type TenantCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantCountOutputType
     */
    select?: TenantCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * TenantCountOutputType without action
   */
  export type TenantCountOutputTypeCountUsersArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TenantUserWhereInput
  }

  /**
   * TenantCountOutputType without action
   */
  export type TenantCountOutputTypeCountInvitesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TenantInviteWhereInput
  }

  /**
   * TenantCountOutputType without action
   */
  export type TenantCountOutputTypeCountAnnotationsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: AnnotationWhereInput
  }

  /**
   * TenantCountOutputType without action
   */
  export type TenantCountOutputTypeCountReportViewsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: ReportViewWhereInput
  }


  /**
   * Count Type UserCountOutputType
   */

  export type UserCountOutputType = {
    tenants: number
    sessions: number
    magicLinks: number
    invites: number
  }

  export type UserCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenants?: boolean | UserCountOutputTypeCountTenantsArgs
    sessions?: boolean | UserCountOutputTypeCountSessionsArgs
    magicLinks?: boolean | UserCountOutputTypeCountMagicLinksArgs
    invites?: boolean | UserCountOutputTypeCountInvitesArgs
  }

  // Custom InputTypes
  /**
   * UserCountOutputType without action
   */
  export type UserCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the UserCountOutputType
     */
    select?: UserCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * UserCountOutputType without action
   */
  export type UserCountOutputTypeCountTenantsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TenantUserWhereInput
  }

  /**
   * UserCountOutputType without action
   */
  export type UserCountOutputTypeCountSessionsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: SessionWhereInput
  }

  /**
   * UserCountOutputType without action
   */
  export type UserCountOutputTypeCountMagicLinksArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: MagicLinkWhereInput
  }

  /**
   * UserCountOutputType without action
   */
  export type UserCountOutputTypeCountInvitesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TenantInviteWhereInput
  }


  /**
   * Models
   */

  /**
   * Model Tenant
   */

  export type AggregateTenant = {
    _count: TenantCountAggregateOutputType | null
    _min: TenantMinAggregateOutputType | null
    _max: TenantMaxAggregateOutputType | null
  }

  export type TenantMinAggregateOutputType = {
    id: string | null
    name: string | null
    slug: string | null
    domain: string | null
    engineTenantId: string | null
    status: $Enums.TenantStatus | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type TenantMaxAggregateOutputType = {
    id: string | null
    name: string | null
    slug: string | null
    domain: string | null
    engineTenantId: string | null
    status: $Enums.TenantStatus | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type TenantCountAggregateOutputType = {
    id: number
    name: number
    slug: number
    domain: number
    engineTenantId: number
    settings: number
    status: number
    createdAt: number
    updatedAt: number
    _all: number
  }


  export type TenantMinAggregateInputType = {
    id?: true
    name?: true
    slug?: true
    domain?: true
    engineTenantId?: true
    status?: true
    createdAt?: true
    updatedAt?: true
  }

  export type TenantMaxAggregateInputType = {
    id?: true
    name?: true
    slug?: true
    domain?: true
    engineTenantId?: true
    status?: true
    createdAt?: true
    updatedAt?: true
  }

  export type TenantCountAggregateInputType = {
    id?: true
    name?: true
    slug?: true
    domain?: true
    engineTenantId?: true
    settings?: true
    status?: true
    createdAt?: true
    updatedAt?: true
    _all?: true
  }

  export type TenantAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Tenant to aggregate.
     */
    where?: TenantWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Tenants to fetch.
     */
    orderBy?: TenantOrderByWithRelationInput | TenantOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: TenantWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Tenants from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Tenants.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Tenants
    **/
    _count?: true | TenantCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: TenantMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: TenantMaxAggregateInputType
  }

  export type GetTenantAggregateType<T extends TenantAggregateArgs> = {
        [P in keyof T & keyof AggregateTenant]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateTenant[P]>
      : GetScalarType<T[P], AggregateTenant[P]>
  }




  export type TenantGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TenantWhereInput
    orderBy?: TenantOrderByWithAggregationInput | TenantOrderByWithAggregationInput[]
    by: TenantScalarFieldEnum[] | TenantScalarFieldEnum
    having?: TenantScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: TenantCountAggregateInputType | true
    _min?: TenantMinAggregateInputType
    _max?: TenantMaxAggregateInputType
  }

  export type TenantGroupByOutputType = {
    id: string
    name: string
    slug: string
    domain: string | null
    engineTenantId: string | null
    settings: JsonValue
    status: $Enums.TenantStatus
    createdAt: Date
    updatedAt: Date
    _count: TenantCountAggregateOutputType | null
    _min: TenantMinAggregateOutputType | null
    _max: TenantMaxAggregateOutputType | null
  }

  type GetTenantGroupByPayload<T extends TenantGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<TenantGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof TenantGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], TenantGroupByOutputType[P]>
            : GetScalarType<T[P], TenantGroupByOutputType[P]>
        }
      >
    >


  export type TenantSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    slug?: boolean
    domain?: boolean
    engineTenantId?: boolean
    settings?: boolean
    status?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    users?: boolean | Tenant$usersArgs<ExtArgs>
    invites?: boolean | Tenant$invitesArgs<ExtArgs>
    annotations?: boolean | Tenant$annotationsArgs<ExtArgs>
    reportViews?: boolean | Tenant$reportViewsArgs<ExtArgs>
    _count?: boolean | TenantCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["tenant"]>

  export type TenantSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    slug?: boolean
    domain?: boolean
    engineTenantId?: boolean
    settings?: boolean
    status?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["tenant"]>

  export type TenantSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    slug?: boolean
    domain?: boolean
    engineTenantId?: boolean
    settings?: boolean
    status?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["tenant"]>

  export type TenantSelectScalar = {
    id?: boolean
    name?: boolean
    slug?: boolean
    domain?: boolean
    engineTenantId?: boolean
    settings?: boolean
    status?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }

  export type TenantOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "name" | "slug" | "domain" | "engineTenantId" | "settings" | "status" | "createdAt" | "updatedAt", ExtArgs["result"]["tenant"]>
  export type TenantInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    users?: boolean | Tenant$usersArgs<ExtArgs>
    invites?: boolean | Tenant$invitesArgs<ExtArgs>
    annotations?: boolean | Tenant$annotationsArgs<ExtArgs>
    reportViews?: boolean | Tenant$reportViewsArgs<ExtArgs>
    _count?: boolean | TenantCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type TenantIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}
  export type TenantIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}

  export type $TenantPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Tenant"
    objects: {
      users: Prisma.$TenantUserPayload<ExtArgs>[]
      invites: Prisma.$TenantInvitePayload<ExtArgs>[]
      annotations: Prisma.$AnnotationPayload<ExtArgs>[]
      reportViews: Prisma.$ReportViewPayload<ExtArgs>[]
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      name: string
      slug: string
      domain: string | null
      engineTenantId: string | null
      settings: Prisma.JsonValue
      status: $Enums.TenantStatus
      createdAt: Date
      updatedAt: Date
    }, ExtArgs["result"]["tenant"]>
    composites: {}
  }

  type TenantGetPayload<S extends boolean | null | undefined | TenantDefaultArgs> = $Result.GetResult<Prisma.$TenantPayload, S>

  type TenantCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<TenantFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: TenantCountAggregateInputType | true
    }

  export interface TenantDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Tenant'], meta: { name: 'Tenant' } }
    /**
     * Find zero or one Tenant that matches the filter.
     * @param {TenantFindUniqueArgs} args - Arguments to find a Tenant
     * @example
     * // Get one Tenant
     * const tenant = await prisma.tenant.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends TenantFindUniqueArgs>(args: SelectSubset<T, TenantFindUniqueArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Tenant that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {TenantFindUniqueOrThrowArgs} args - Arguments to find a Tenant
     * @example
     * // Get one Tenant
     * const tenant = await prisma.tenant.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends TenantFindUniqueOrThrowArgs>(args: SelectSubset<T, TenantFindUniqueOrThrowArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Tenant that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantFindFirstArgs} args - Arguments to find a Tenant
     * @example
     * // Get one Tenant
     * const tenant = await prisma.tenant.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends TenantFindFirstArgs>(args?: SelectSubset<T, TenantFindFirstArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Tenant that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantFindFirstOrThrowArgs} args - Arguments to find a Tenant
     * @example
     * // Get one Tenant
     * const tenant = await prisma.tenant.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends TenantFindFirstOrThrowArgs>(args?: SelectSubset<T, TenantFindFirstOrThrowArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Tenants that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Tenants
     * const tenants = await prisma.tenant.findMany()
     * 
     * // Get first 10 Tenants
     * const tenants = await prisma.tenant.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const tenantWithIdOnly = await prisma.tenant.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends TenantFindManyArgs>(args?: SelectSubset<T, TenantFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Tenant.
     * @param {TenantCreateArgs} args - Arguments to create a Tenant.
     * @example
     * // Create one Tenant
     * const Tenant = await prisma.tenant.create({
     *   data: {
     *     // ... data to create a Tenant
     *   }
     * })
     * 
     */
    create<T extends TenantCreateArgs>(args: SelectSubset<T, TenantCreateArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Tenants.
     * @param {TenantCreateManyArgs} args - Arguments to create many Tenants.
     * @example
     * // Create many Tenants
     * const tenant = await prisma.tenant.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends TenantCreateManyArgs>(args?: SelectSubset<T, TenantCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Tenants and returns the data saved in the database.
     * @param {TenantCreateManyAndReturnArgs} args - Arguments to create many Tenants.
     * @example
     * // Create many Tenants
     * const tenant = await prisma.tenant.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Tenants and only return the `id`
     * const tenantWithIdOnly = await prisma.tenant.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends TenantCreateManyAndReturnArgs>(args?: SelectSubset<T, TenantCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Tenant.
     * @param {TenantDeleteArgs} args - Arguments to delete one Tenant.
     * @example
     * // Delete one Tenant
     * const Tenant = await prisma.tenant.delete({
     *   where: {
     *     // ... filter to delete one Tenant
     *   }
     * })
     * 
     */
    delete<T extends TenantDeleteArgs>(args: SelectSubset<T, TenantDeleteArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Tenant.
     * @param {TenantUpdateArgs} args - Arguments to update one Tenant.
     * @example
     * // Update one Tenant
     * const tenant = await prisma.tenant.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends TenantUpdateArgs>(args: SelectSubset<T, TenantUpdateArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Tenants.
     * @param {TenantDeleteManyArgs} args - Arguments to filter Tenants to delete.
     * @example
     * // Delete a few Tenants
     * const { count } = await prisma.tenant.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends TenantDeleteManyArgs>(args?: SelectSubset<T, TenantDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Tenants.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Tenants
     * const tenant = await prisma.tenant.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends TenantUpdateManyArgs>(args: SelectSubset<T, TenantUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Tenants and returns the data updated in the database.
     * @param {TenantUpdateManyAndReturnArgs} args - Arguments to update many Tenants.
     * @example
     * // Update many Tenants
     * const tenant = await prisma.tenant.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Tenants and only return the `id`
     * const tenantWithIdOnly = await prisma.tenant.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends TenantUpdateManyAndReturnArgs>(args: SelectSubset<T, TenantUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Tenant.
     * @param {TenantUpsertArgs} args - Arguments to update or create a Tenant.
     * @example
     * // Update or create a Tenant
     * const tenant = await prisma.tenant.upsert({
     *   create: {
     *     // ... data to create a Tenant
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Tenant we want to update
     *   }
     * })
     */
    upsert<T extends TenantUpsertArgs>(args: SelectSubset<T, TenantUpsertArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Tenants.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantCountArgs} args - Arguments to filter Tenants to count.
     * @example
     * // Count the number of Tenants
     * const count = await prisma.tenant.count({
     *   where: {
     *     // ... the filter for the Tenants we want to count
     *   }
     * })
    **/
    count<T extends TenantCountArgs>(
      args?: Subset<T, TenantCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], TenantCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Tenant.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends TenantAggregateArgs>(args: Subset<T, TenantAggregateArgs>): Prisma.PrismaPromise<GetTenantAggregateType<T>>

    /**
     * Group by Tenant.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends TenantGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: TenantGroupByArgs['orderBy'] }
        : { orderBy?: TenantGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, TenantGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetTenantGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Tenant model
   */
  readonly fields: TenantFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Tenant.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__TenantClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    users<T extends Tenant$usersArgs<ExtArgs> = {}>(args?: Subset<T, Tenant$usersArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    invites<T extends Tenant$invitesArgs<ExtArgs> = {}>(args?: Subset<T, Tenant$invitesArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    annotations<T extends Tenant$annotationsArgs<ExtArgs> = {}>(args?: Subset<T, Tenant$annotationsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    reportViews<T extends Tenant$reportViewsArgs<ExtArgs> = {}>(args?: Subset<T, Tenant$reportViewsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Tenant model
   */
  interface TenantFieldRefs {
    readonly id: FieldRef<"Tenant", 'String'>
    readonly name: FieldRef<"Tenant", 'String'>
    readonly slug: FieldRef<"Tenant", 'String'>
    readonly domain: FieldRef<"Tenant", 'String'>
    readonly engineTenantId: FieldRef<"Tenant", 'String'>
    readonly settings: FieldRef<"Tenant", 'Json'>
    readonly status: FieldRef<"Tenant", 'TenantStatus'>
    readonly createdAt: FieldRef<"Tenant", 'DateTime'>
    readonly updatedAt: FieldRef<"Tenant", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * Tenant findUnique
   */
  export type TenantFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInclude<ExtArgs> | null
    /**
     * Filter, which Tenant to fetch.
     */
    where: TenantWhereUniqueInput
  }

  /**
   * Tenant findUniqueOrThrow
   */
  export type TenantFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInclude<ExtArgs> | null
    /**
     * Filter, which Tenant to fetch.
     */
    where: TenantWhereUniqueInput
  }

  /**
   * Tenant findFirst
   */
  export type TenantFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInclude<ExtArgs> | null
    /**
     * Filter, which Tenant to fetch.
     */
    where?: TenantWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Tenants to fetch.
     */
    orderBy?: TenantOrderByWithRelationInput | TenantOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Tenants.
     */
    cursor?: TenantWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Tenants from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Tenants.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Tenants.
     */
    distinct?: TenantScalarFieldEnum | TenantScalarFieldEnum[]
  }

  /**
   * Tenant findFirstOrThrow
   */
  export type TenantFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInclude<ExtArgs> | null
    /**
     * Filter, which Tenant to fetch.
     */
    where?: TenantWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Tenants to fetch.
     */
    orderBy?: TenantOrderByWithRelationInput | TenantOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Tenants.
     */
    cursor?: TenantWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Tenants from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Tenants.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Tenants.
     */
    distinct?: TenantScalarFieldEnum | TenantScalarFieldEnum[]
  }

  /**
   * Tenant findMany
   */
  export type TenantFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInclude<ExtArgs> | null
    /**
     * Filter, which Tenants to fetch.
     */
    where?: TenantWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Tenants to fetch.
     */
    orderBy?: TenantOrderByWithRelationInput | TenantOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Tenants.
     */
    cursor?: TenantWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Tenants from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Tenants.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Tenants.
     */
    distinct?: TenantScalarFieldEnum | TenantScalarFieldEnum[]
  }

  /**
   * Tenant create
   */
  export type TenantCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInclude<ExtArgs> | null
    /**
     * The data needed to create a Tenant.
     */
    data: XOR<TenantCreateInput, TenantUncheckedCreateInput>
  }

  /**
   * Tenant createMany
   */
  export type TenantCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Tenants.
     */
    data: TenantCreateManyInput | TenantCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Tenant createManyAndReturn
   */
  export type TenantCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * The data used to create many Tenants.
     */
    data: TenantCreateManyInput | TenantCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Tenant update
   */
  export type TenantUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInclude<ExtArgs> | null
    /**
     * The data needed to update a Tenant.
     */
    data: XOR<TenantUpdateInput, TenantUncheckedUpdateInput>
    /**
     * Choose, which Tenant to update.
     */
    where: TenantWhereUniqueInput
  }

  /**
   * Tenant updateMany
   */
  export type TenantUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Tenants.
     */
    data: XOR<TenantUpdateManyMutationInput, TenantUncheckedUpdateManyInput>
    /**
     * Filter which Tenants to update
     */
    where?: TenantWhereInput
    /**
     * Limit how many Tenants to update.
     */
    limit?: number
  }

  /**
   * Tenant updateManyAndReturn
   */
  export type TenantUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * The data used to update Tenants.
     */
    data: XOR<TenantUpdateManyMutationInput, TenantUncheckedUpdateManyInput>
    /**
     * Filter which Tenants to update
     */
    where?: TenantWhereInput
    /**
     * Limit how many Tenants to update.
     */
    limit?: number
  }

  /**
   * Tenant upsert
   */
  export type TenantUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInclude<ExtArgs> | null
    /**
     * The filter to search for the Tenant to update in case it exists.
     */
    where: TenantWhereUniqueInput
    /**
     * In case the Tenant found by the `where` argument doesn't exist, create a new Tenant with this data.
     */
    create: XOR<TenantCreateInput, TenantUncheckedCreateInput>
    /**
     * In case the Tenant was found with the provided `where` argument, update it with this data.
     */
    update: XOR<TenantUpdateInput, TenantUncheckedUpdateInput>
  }

  /**
   * Tenant delete
   */
  export type TenantDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInclude<ExtArgs> | null
    /**
     * Filter which Tenant to delete.
     */
    where: TenantWhereUniqueInput
  }

  /**
   * Tenant deleteMany
   */
  export type TenantDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Tenants to delete
     */
    where?: TenantWhereInput
    /**
     * Limit how many Tenants to delete.
     */
    limit?: number
  }

  /**
   * Tenant.users
   */
  export type Tenant$usersArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    where?: TenantUserWhereInput
    orderBy?: TenantUserOrderByWithRelationInput | TenantUserOrderByWithRelationInput[]
    cursor?: TenantUserWhereUniqueInput
    take?: number
    skip?: number
    distinct?: TenantUserScalarFieldEnum | TenantUserScalarFieldEnum[]
  }

  /**
   * Tenant.invites
   */
  export type Tenant$invitesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    where?: TenantInviteWhereInput
    orderBy?: TenantInviteOrderByWithRelationInput | TenantInviteOrderByWithRelationInput[]
    cursor?: TenantInviteWhereUniqueInput
    take?: number
    skip?: number
    distinct?: TenantInviteScalarFieldEnum | TenantInviteScalarFieldEnum[]
  }

  /**
   * Tenant.annotations
   */
  export type Tenant$annotationsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
    where?: AnnotationWhereInput
    orderBy?: AnnotationOrderByWithRelationInput | AnnotationOrderByWithRelationInput[]
    cursor?: AnnotationWhereUniqueInput
    take?: number
    skip?: number
    distinct?: AnnotationScalarFieldEnum | AnnotationScalarFieldEnum[]
  }

  /**
   * Tenant.reportViews
   */
  export type Tenant$reportViewsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
    where?: ReportViewWhereInput
    orderBy?: ReportViewOrderByWithRelationInput | ReportViewOrderByWithRelationInput[]
    cursor?: ReportViewWhereUniqueInput
    take?: number
    skip?: number
    distinct?: ReportViewScalarFieldEnum | ReportViewScalarFieldEnum[]
  }

  /**
   * Tenant without action
   */
  export type TenantDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Tenant
     */
    select?: TenantSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Tenant
     */
    omit?: TenantOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInclude<ExtArgs> | null
  }


  /**
   * Model User
   */

  export type AggregateUser = {
    _count: UserCountAggregateOutputType | null
    _min: UserMinAggregateOutputType | null
    _max: UserMaxAggregateOutputType | null
  }

  export type UserMinAggregateOutputType = {
    id: string | null
    email: string | null
    name: string | null
    avatarUrl: string | null
    isSuperAdmin: boolean | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type UserMaxAggregateOutputType = {
    id: string | null
    email: string | null
    name: string | null
    avatarUrl: string | null
    isSuperAdmin: boolean | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type UserCountAggregateOutputType = {
    id: number
    email: number
    name: number
    avatarUrl: number
    isSuperAdmin: number
    createdAt: number
    updatedAt: number
    _all: number
  }


  export type UserMinAggregateInputType = {
    id?: true
    email?: true
    name?: true
    avatarUrl?: true
    isSuperAdmin?: true
    createdAt?: true
    updatedAt?: true
  }

  export type UserMaxAggregateInputType = {
    id?: true
    email?: true
    name?: true
    avatarUrl?: true
    isSuperAdmin?: true
    createdAt?: true
    updatedAt?: true
  }

  export type UserCountAggregateInputType = {
    id?: true
    email?: true
    name?: true
    avatarUrl?: true
    isSuperAdmin?: true
    createdAt?: true
    updatedAt?: true
    _all?: true
  }

  export type UserAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which User to aggregate.
     */
    where?: UserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Users to fetch.
     */
    orderBy?: UserOrderByWithRelationInput | UserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: UserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Users from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Users.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Users
    **/
    _count?: true | UserCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: UserMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: UserMaxAggregateInputType
  }

  export type GetUserAggregateType<T extends UserAggregateArgs> = {
        [P in keyof T & keyof AggregateUser]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateUser[P]>
      : GetScalarType<T[P], AggregateUser[P]>
  }




  export type UserGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: UserWhereInput
    orderBy?: UserOrderByWithAggregationInput | UserOrderByWithAggregationInput[]
    by: UserScalarFieldEnum[] | UserScalarFieldEnum
    having?: UserScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: UserCountAggregateInputType | true
    _min?: UserMinAggregateInputType
    _max?: UserMaxAggregateInputType
  }

  export type UserGroupByOutputType = {
    id: string
    email: string
    name: string | null
    avatarUrl: string | null
    isSuperAdmin: boolean
    createdAt: Date
    updatedAt: Date
    _count: UserCountAggregateOutputType | null
    _min: UserMinAggregateOutputType | null
    _max: UserMaxAggregateOutputType | null
  }

  type GetUserGroupByPayload<T extends UserGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<UserGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof UserGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], UserGroupByOutputType[P]>
            : GetScalarType<T[P], UserGroupByOutputType[P]>
        }
      >
    >


  export type UserSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    email?: boolean
    name?: boolean
    avatarUrl?: boolean
    isSuperAdmin?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    tenants?: boolean | User$tenantsArgs<ExtArgs>
    sessions?: boolean | User$sessionsArgs<ExtArgs>
    magicLinks?: boolean | User$magicLinksArgs<ExtArgs>
    invites?: boolean | User$invitesArgs<ExtArgs>
    _count?: boolean | UserCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["user"]>

  export type UserSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    email?: boolean
    name?: boolean
    avatarUrl?: boolean
    isSuperAdmin?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["user"]>

  export type UserSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    email?: boolean
    name?: boolean
    avatarUrl?: boolean
    isSuperAdmin?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["user"]>

  export type UserSelectScalar = {
    id?: boolean
    email?: boolean
    name?: boolean
    avatarUrl?: boolean
    isSuperAdmin?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }

  export type UserOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "email" | "name" | "avatarUrl" | "isSuperAdmin" | "createdAt" | "updatedAt", ExtArgs["result"]["user"]>
  export type UserInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenants?: boolean | User$tenantsArgs<ExtArgs>
    sessions?: boolean | User$sessionsArgs<ExtArgs>
    magicLinks?: boolean | User$magicLinksArgs<ExtArgs>
    invites?: boolean | User$invitesArgs<ExtArgs>
    _count?: boolean | UserCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type UserIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}
  export type UserIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}

  export type $UserPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "User"
    objects: {
      tenants: Prisma.$TenantUserPayload<ExtArgs>[]
      sessions: Prisma.$SessionPayload<ExtArgs>[]
      magicLinks: Prisma.$MagicLinkPayload<ExtArgs>[]
      invites: Prisma.$TenantInvitePayload<ExtArgs>[]
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      email: string
      name: string | null
      avatarUrl: string | null
      isSuperAdmin: boolean
      createdAt: Date
      updatedAt: Date
    }, ExtArgs["result"]["user"]>
    composites: {}
  }

  type UserGetPayload<S extends boolean | null | undefined | UserDefaultArgs> = $Result.GetResult<Prisma.$UserPayload, S>

  type UserCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<UserFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: UserCountAggregateInputType | true
    }

  export interface UserDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['User'], meta: { name: 'User' } }
    /**
     * Find zero or one User that matches the filter.
     * @param {UserFindUniqueArgs} args - Arguments to find a User
     * @example
     * // Get one User
     * const user = await prisma.user.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends UserFindUniqueArgs>(args: SelectSubset<T, UserFindUniqueArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one User that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {UserFindUniqueOrThrowArgs} args - Arguments to find a User
     * @example
     * // Get one User
     * const user = await prisma.user.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends UserFindUniqueOrThrowArgs>(args: SelectSubset<T, UserFindUniqueOrThrowArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first User that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserFindFirstArgs} args - Arguments to find a User
     * @example
     * // Get one User
     * const user = await prisma.user.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends UserFindFirstArgs>(args?: SelectSubset<T, UserFindFirstArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first User that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserFindFirstOrThrowArgs} args - Arguments to find a User
     * @example
     * // Get one User
     * const user = await prisma.user.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends UserFindFirstOrThrowArgs>(args?: SelectSubset<T, UserFindFirstOrThrowArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Users that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Users
     * const users = await prisma.user.findMany()
     * 
     * // Get first 10 Users
     * const users = await prisma.user.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const userWithIdOnly = await prisma.user.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends UserFindManyArgs>(args?: SelectSubset<T, UserFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a User.
     * @param {UserCreateArgs} args - Arguments to create a User.
     * @example
     * // Create one User
     * const User = await prisma.user.create({
     *   data: {
     *     // ... data to create a User
     *   }
     * })
     * 
     */
    create<T extends UserCreateArgs>(args: SelectSubset<T, UserCreateArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Users.
     * @param {UserCreateManyArgs} args - Arguments to create many Users.
     * @example
     * // Create many Users
     * const user = await prisma.user.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends UserCreateManyArgs>(args?: SelectSubset<T, UserCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Users and returns the data saved in the database.
     * @param {UserCreateManyAndReturnArgs} args - Arguments to create many Users.
     * @example
     * // Create many Users
     * const user = await prisma.user.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Users and only return the `id`
     * const userWithIdOnly = await prisma.user.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends UserCreateManyAndReturnArgs>(args?: SelectSubset<T, UserCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a User.
     * @param {UserDeleteArgs} args - Arguments to delete one User.
     * @example
     * // Delete one User
     * const User = await prisma.user.delete({
     *   where: {
     *     // ... filter to delete one User
     *   }
     * })
     * 
     */
    delete<T extends UserDeleteArgs>(args: SelectSubset<T, UserDeleteArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one User.
     * @param {UserUpdateArgs} args - Arguments to update one User.
     * @example
     * // Update one User
     * const user = await prisma.user.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends UserUpdateArgs>(args: SelectSubset<T, UserUpdateArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Users.
     * @param {UserDeleteManyArgs} args - Arguments to filter Users to delete.
     * @example
     * // Delete a few Users
     * const { count } = await prisma.user.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends UserDeleteManyArgs>(args?: SelectSubset<T, UserDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Users.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Users
     * const user = await prisma.user.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends UserUpdateManyArgs>(args: SelectSubset<T, UserUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Users and returns the data updated in the database.
     * @param {UserUpdateManyAndReturnArgs} args - Arguments to update many Users.
     * @example
     * // Update many Users
     * const user = await prisma.user.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Users and only return the `id`
     * const userWithIdOnly = await prisma.user.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends UserUpdateManyAndReturnArgs>(args: SelectSubset<T, UserUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one User.
     * @param {UserUpsertArgs} args - Arguments to update or create a User.
     * @example
     * // Update or create a User
     * const user = await prisma.user.upsert({
     *   create: {
     *     // ... data to create a User
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the User we want to update
     *   }
     * })
     */
    upsert<T extends UserUpsertArgs>(args: SelectSubset<T, UserUpsertArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Users.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserCountArgs} args - Arguments to filter Users to count.
     * @example
     * // Count the number of Users
     * const count = await prisma.user.count({
     *   where: {
     *     // ... the filter for the Users we want to count
     *   }
     * })
    **/
    count<T extends UserCountArgs>(
      args?: Subset<T, UserCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], UserCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a User.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends UserAggregateArgs>(args: Subset<T, UserAggregateArgs>): Prisma.PrismaPromise<GetUserAggregateType<T>>

    /**
     * Group by User.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends UserGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: UserGroupByArgs['orderBy'] }
        : { orderBy?: UserGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, UserGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetUserGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the User model
   */
  readonly fields: UserFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for User.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__UserClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    tenants<T extends User$tenantsArgs<ExtArgs> = {}>(args?: Subset<T, User$tenantsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    sessions<T extends User$sessionsArgs<ExtArgs> = {}>(args?: Subset<T, User$sessionsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    magicLinks<T extends User$magicLinksArgs<ExtArgs> = {}>(args?: Subset<T, User$magicLinksArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    invites<T extends User$invitesArgs<ExtArgs> = {}>(args?: Subset<T, User$invitesArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the User model
   */
  interface UserFieldRefs {
    readonly id: FieldRef<"User", 'String'>
    readonly email: FieldRef<"User", 'String'>
    readonly name: FieldRef<"User", 'String'>
    readonly avatarUrl: FieldRef<"User", 'String'>
    readonly isSuperAdmin: FieldRef<"User", 'Boolean'>
    readonly createdAt: FieldRef<"User", 'DateTime'>
    readonly updatedAt: FieldRef<"User", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * User findUnique
   */
  export type UserFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter, which User to fetch.
     */
    where: UserWhereUniqueInput
  }

  /**
   * User findUniqueOrThrow
   */
  export type UserFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter, which User to fetch.
     */
    where: UserWhereUniqueInput
  }

  /**
   * User findFirst
   */
  export type UserFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter, which User to fetch.
     */
    where?: UserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Users to fetch.
     */
    orderBy?: UserOrderByWithRelationInput | UserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Users.
     */
    cursor?: UserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Users from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Users.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Users.
     */
    distinct?: UserScalarFieldEnum | UserScalarFieldEnum[]
  }

  /**
   * User findFirstOrThrow
   */
  export type UserFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter, which User to fetch.
     */
    where?: UserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Users to fetch.
     */
    orderBy?: UserOrderByWithRelationInput | UserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Users.
     */
    cursor?: UserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Users from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Users.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Users.
     */
    distinct?: UserScalarFieldEnum | UserScalarFieldEnum[]
  }

  /**
   * User findMany
   */
  export type UserFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter, which Users to fetch.
     */
    where?: UserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Users to fetch.
     */
    orderBy?: UserOrderByWithRelationInput | UserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Users.
     */
    cursor?: UserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Users from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Users.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Users.
     */
    distinct?: UserScalarFieldEnum | UserScalarFieldEnum[]
  }

  /**
   * User create
   */
  export type UserCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * The data needed to create a User.
     */
    data: XOR<UserCreateInput, UserUncheckedCreateInput>
  }

  /**
   * User createMany
   */
  export type UserCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Users.
     */
    data: UserCreateManyInput | UserCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * User createManyAndReturn
   */
  export type UserCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * The data used to create many Users.
     */
    data: UserCreateManyInput | UserCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * User update
   */
  export type UserUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * The data needed to update a User.
     */
    data: XOR<UserUpdateInput, UserUncheckedUpdateInput>
    /**
     * Choose, which User to update.
     */
    where: UserWhereUniqueInput
  }

  /**
   * User updateMany
   */
  export type UserUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Users.
     */
    data: XOR<UserUpdateManyMutationInput, UserUncheckedUpdateManyInput>
    /**
     * Filter which Users to update
     */
    where?: UserWhereInput
    /**
     * Limit how many Users to update.
     */
    limit?: number
  }

  /**
   * User updateManyAndReturn
   */
  export type UserUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * The data used to update Users.
     */
    data: XOR<UserUpdateManyMutationInput, UserUncheckedUpdateManyInput>
    /**
     * Filter which Users to update
     */
    where?: UserWhereInput
    /**
     * Limit how many Users to update.
     */
    limit?: number
  }

  /**
   * User upsert
   */
  export type UserUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * The filter to search for the User to update in case it exists.
     */
    where: UserWhereUniqueInput
    /**
     * In case the User found by the `where` argument doesn't exist, create a new User with this data.
     */
    create: XOR<UserCreateInput, UserUncheckedCreateInput>
    /**
     * In case the User was found with the provided `where` argument, update it with this data.
     */
    update: XOR<UserUpdateInput, UserUncheckedUpdateInput>
  }

  /**
   * User delete
   */
  export type UserDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter which User to delete.
     */
    where: UserWhereUniqueInput
  }

  /**
   * User deleteMany
   */
  export type UserDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Users to delete
     */
    where?: UserWhereInput
    /**
     * Limit how many Users to delete.
     */
    limit?: number
  }

  /**
   * User.tenants
   */
  export type User$tenantsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    where?: TenantUserWhereInput
    orderBy?: TenantUserOrderByWithRelationInput | TenantUserOrderByWithRelationInput[]
    cursor?: TenantUserWhereUniqueInput
    take?: number
    skip?: number
    distinct?: TenantUserScalarFieldEnum | TenantUserScalarFieldEnum[]
  }

  /**
   * User.sessions
   */
  export type User$sessionsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    where?: SessionWhereInput
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    cursor?: SessionWhereUniqueInput
    take?: number
    skip?: number
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * User.magicLinks
   */
  export type User$magicLinksArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
    where?: MagicLinkWhereInput
    orderBy?: MagicLinkOrderByWithRelationInput | MagicLinkOrderByWithRelationInput[]
    cursor?: MagicLinkWhereUniqueInput
    take?: number
    skip?: number
    distinct?: MagicLinkScalarFieldEnum | MagicLinkScalarFieldEnum[]
  }

  /**
   * User.invites
   */
  export type User$invitesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    where?: TenantInviteWhereInput
    orderBy?: TenantInviteOrderByWithRelationInput | TenantInviteOrderByWithRelationInput[]
    cursor?: TenantInviteWhereUniqueInput
    take?: number
    skip?: number
    distinct?: TenantInviteScalarFieldEnum | TenantInviteScalarFieldEnum[]
  }

  /**
   * User without action
   */
  export type UserDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
  }


  /**
   * Model TenantUser
   */

  export type AggregateTenantUser = {
    _count: TenantUserCountAggregateOutputType | null
    _min: TenantUserMinAggregateOutputType | null
    _max: TenantUserMaxAggregateOutputType | null
  }

  export type TenantUserMinAggregateOutputType = {
    id: string | null
    userId: string | null
    tenantId: string | null
    role: $Enums.TenantRole | null
    joinedAt: Date | null
  }

  export type TenantUserMaxAggregateOutputType = {
    id: string | null
    userId: string | null
    tenantId: string | null
    role: $Enums.TenantRole | null
    joinedAt: Date | null
  }

  export type TenantUserCountAggregateOutputType = {
    id: number
    userId: number
    tenantId: number
    role: number
    joinedAt: number
    _all: number
  }


  export type TenantUserMinAggregateInputType = {
    id?: true
    userId?: true
    tenantId?: true
    role?: true
    joinedAt?: true
  }

  export type TenantUserMaxAggregateInputType = {
    id?: true
    userId?: true
    tenantId?: true
    role?: true
    joinedAt?: true
  }

  export type TenantUserCountAggregateInputType = {
    id?: true
    userId?: true
    tenantId?: true
    role?: true
    joinedAt?: true
    _all?: true
  }

  export type TenantUserAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which TenantUser to aggregate.
     */
    where?: TenantUserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TenantUsers to fetch.
     */
    orderBy?: TenantUserOrderByWithRelationInput | TenantUserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: TenantUserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TenantUsers from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TenantUsers.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned TenantUsers
    **/
    _count?: true | TenantUserCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: TenantUserMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: TenantUserMaxAggregateInputType
  }

  export type GetTenantUserAggregateType<T extends TenantUserAggregateArgs> = {
        [P in keyof T & keyof AggregateTenantUser]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateTenantUser[P]>
      : GetScalarType<T[P], AggregateTenantUser[P]>
  }




  export type TenantUserGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TenantUserWhereInput
    orderBy?: TenantUserOrderByWithAggregationInput | TenantUserOrderByWithAggregationInput[]
    by: TenantUserScalarFieldEnum[] | TenantUserScalarFieldEnum
    having?: TenantUserScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: TenantUserCountAggregateInputType | true
    _min?: TenantUserMinAggregateInputType
    _max?: TenantUserMaxAggregateInputType
  }

  export type TenantUserGroupByOutputType = {
    id: string
    userId: string
    tenantId: string
    role: $Enums.TenantRole
    joinedAt: Date
    _count: TenantUserCountAggregateOutputType | null
    _min: TenantUserMinAggregateOutputType | null
    _max: TenantUserMaxAggregateOutputType | null
  }

  type GetTenantUserGroupByPayload<T extends TenantUserGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<TenantUserGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof TenantUserGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], TenantUserGroupByOutputType[P]>
            : GetScalarType<T[P], TenantUserGroupByOutputType[P]>
        }
      >
    >


  export type TenantUserSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    tenantId?: boolean
    role?: boolean
    joinedAt?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["tenantUser"]>

  export type TenantUserSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    tenantId?: boolean
    role?: boolean
    joinedAt?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["tenantUser"]>

  export type TenantUserSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    tenantId?: boolean
    role?: boolean
    joinedAt?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["tenantUser"]>

  export type TenantUserSelectScalar = {
    id?: boolean
    userId?: boolean
    tenantId?: boolean
    role?: boolean
    joinedAt?: boolean
  }

  export type TenantUserOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "userId" | "tenantId" | "role" | "joinedAt", ExtArgs["result"]["tenantUser"]>
  export type TenantUserInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }
  export type TenantUserIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }
  export type TenantUserIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }

  export type $TenantUserPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "TenantUser"
    objects: {
      user: Prisma.$UserPayload<ExtArgs>
      tenant: Prisma.$TenantPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      userId: string
      tenantId: string
      role: $Enums.TenantRole
      joinedAt: Date
    }, ExtArgs["result"]["tenantUser"]>
    composites: {}
  }

  type TenantUserGetPayload<S extends boolean | null | undefined | TenantUserDefaultArgs> = $Result.GetResult<Prisma.$TenantUserPayload, S>

  type TenantUserCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<TenantUserFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: TenantUserCountAggregateInputType | true
    }

  export interface TenantUserDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['TenantUser'], meta: { name: 'TenantUser' } }
    /**
     * Find zero or one TenantUser that matches the filter.
     * @param {TenantUserFindUniqueArgs} args - Arguments to find a TenantUser
     * @example
     * // Get one TenantUser
     * const tenantUser = await prisma.tenantUser.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends TenantUserFindUniqueArgs>(args: SelectSubset<T, TenantUserFindUniqueArgs<ExtArgs>>): Prisma__TenantUserClient<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one TenantUser that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {TenantUserFindUniqueOrThrowArgs} args - Arguments to find a TenantUser
     * @example
     * // Get one TenantUser
     * const tenantUser = await prisma.tenantUser.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends TenantUserFindUniqueOrThrowArgs>(args: SelectSubset<T, TenantUserFindUniqueOrThrowArgs<ExtArgs>>): Prisma__TenantUserClient<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first TenantUser that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantUserFindFirstArgs} args - Arguments to find a TenantUser
     * @example
     * // Get one TenantUser
     * const tenantUser = await prisma.tenantUser.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends TenantUserFindFirstArgs>(args?: SelectSubset<T, TenantUserFindFirstArgs<ExtArgs>>): Prisma__TenantUserClient<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first TenantUser that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantUserFindFirstOrThrowArgs} args - Arguments to find a TenantUser
     * @example
     * // Get one TenantUser
     * const tenantUser = await prisma.tenantUser.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends TenantUserFindFirstOrThrowArgs>(args?: SelectSubset<T, TenantUserFindFirstOrThrowArgs<ExtArgs>>): Prisma__TenantUserClient<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more TenantUsers that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantUserFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all TenantUsers
     * const tenantUsers = await prisma.tenantUser.findMany()
     * 
     * // Get first 10 TenantUsers
     * const tenantUsers = await prisma.tenantUser.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const tenantUserWithIdOnly = await prisma.tenantUser.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends TenantUserFindManyArgs>(args?: SelectSubset<T, TenantUserFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a TenantUser.
     * @param {TenantUserCreateArgs} args - Arguments to create a TenantUser.
     * @example
     * // Create one TenantUser
     * const TenantUser = await prisma.tenantUser.create({
     *   data: {
     *     // ... data to create a TenantUser
     *   }
     * })
     * 
     */
    create<T extends TenantUserCreateArgs>(args: SelectSubset<T, TenantUserCreateArgs<ExtArgs>>): Prisma__TenantUserClient<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many TenantUsers.
     * @param {TenantUserCreateManyArgs} args - Arguments to create many TenantUsers.
     * @example
     * // Create many TenantUsers
     * const tenantUser = await prisma.tenantUser.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends TenantUserCreateManyArgs>(args?: SelectSubset<T, TenantUserCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many TenantUsers and returns the data saved in the database.
     * @param {TenantUserCreateManyAndReturnArgs} args - Arguments to create many TenantUsers.
     * @example
     * // Create many TenantUsers
     * const tenantUser = await prisma.tenantUser.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many TenantUsers and only return the `id`
     * const tenantUserWithIdOnly = await prisma.tenantUser.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends TenantUserCreateManyAndReturnArgs>(args?: SelectSubset<T, TenantUserCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a TenantUser.
     * @param {TenantUserDeleteArgs} args - Arguments to delete one TenantUser.
     * @example
     * // Delete one TenantUser
     * const TenantUser = await prisma.tenantUser.delete({
     *   where: {
     *     // ... filter to delete one TenantUser
     *   }
     * })
     * 
     */
    delete<T extends TenantUserDeleteArgs>(args: SelectSubset<T, TenantUserDeleteArgs<ExtArgs>>): Prisma__TenantUserClient<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one TenantUser.
     * @param {TenantUserUpdateArgs} args - Arguments to update one TenantUser.
     * @example
     * // Update one TenantUser
     * const tenantUser = await prisma.tenantUser.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends TenantUserUpdateArgs>(args: SelectSubset<T, TenantUserUpdateArgs<ExtArgs>>): Prisma__TenantUserClient<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more TenantUsers.
     * @param {TenantUserDeleteManyArgs} args - Arguments to filter TenantUsers to delete.
     * @example
     * // Delete a few TenantUsers
     * const { count } = await prisma.tenantUser.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends TenantUserDeleteManyArgs>(args?: SelectSubset<T, TenantUserDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more TenantUsers.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantUserUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many TenantUsers
     * const tenantUser = await prisma.tenantUser.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends TenantUserUpdateManyArgs>(args: SelectSubset<T, TenantUserUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more TenantUsers and returns the data updated in the database.
     * @param {TenantUserUpdateManyAndReturnArgs} args - Arguments to update many TenantUsers.
     * @example
     * // Update many TenantUsers
     * const tenantUser = await prisma.tenantUser.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more TenantUsers and only return the `id`
     * const tenantUserWithIdOnly = await prisma.tenantUser.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends TenantUserUpdateManyAndReturnArgs>(args: SelectSubset<T, TenantUserUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one TenantUser.
     * @param {TenantUserUpsertArgs} args - Arguments to update or create a TenantUser.
     * @example
     * // Update or create a TenantUser
     * const tenantUser = await prisma.tenantUser.upsert({
     *   create: {
     *     // ... data to create a TenantUser
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the TenantUser we want to update
     *   }
     * })
     */
    upsert<T extends TenantUserUpsertArgs>(args: SelectSubset<T, TenantUserUpsertArgs<ExtArgs>>): Prisma__TenantUserClient<$Result.GetResult<Prisma.$TenantUserPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of TenantUsers.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantUserCountArgs} args - Arguments to filter TenantUsers to count.
     * @example
     * // Count the number of TenantUsers
     * const count = await prisma.tenantUser.count({
     *   where: {
     *     // ... the filter for the TenantUsers we want to count
     *   }
     * })
    **/
    count<T extends TenantUserCountArgs>(
      args?: Subset<T, TenantUserCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], TenantUserCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a TenantUser.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantUserAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends TenantUserAggregateArgs>(args: Subset<T, TenantUserAggregateArgs>): Prisma.PrismaPromise<GetTenantUserAggregateType<T>>

    /**
     * Group by TenantUser.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantUserGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends TenantUserGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: TenantUserGroupByArgs['orderBy'] }
        : { orderBy?: TenantUserGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, TenantUserGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetTenantUserGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the TenantUser model
   */
  readonly fields: TenantUserFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for TenantUser.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__TenantUserClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    user<T extends UserDefaultArgs<ExtArgs> = {}>(args?: Subset<T, UserDefaultArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    tenant<T extends TenantDefaultArgs<ExtArgs> = {}>(args?: Subset<T, TenantDefaultArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the TenantUser model
   */
  interface TenantUserFieldRefs {
    readonly id: FieldRef<"TenantUser", 'String'>
    readonly userId: FieldRef<"TenantUser", 'String'>
    readonly tenantId: FieldRef<"TenantUser", 'String'>
    readonly role: FieldRef<"TenantUser", 'TenantRole'>
    readonly joinedAt: FieldRef<"TenantUser", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * TenantUser findUnique
   */
  export type TenantUserFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    /**
     * Filter, which TenantUser to fetch.
     */
    where: TenantUserWhereUniqueInput
  }

  /**
   * TenantUser findUniqueOrThrow
   */
  export type TenantUserFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    /**
     * Filter, which TenantUser to fetch.
     */
    where: TenantUserWhereUniqueInput
  }

  /**
   * TenantUser findFirst
   */
  export type TenantUserFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    /**
     * Filter, which TenantUser to fetch.
     */
    where?: TenantUserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TenantUsers to fetch.
     */
    orderBy?: TenantUserOrderByWithRelationInput | TenantUserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for TenantUsers.
     */
    cursor?: TenantUserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TenantUsers from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TenantUsers.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of TenantUsers.
     */
    distinct?: TenantUserScalarFieldEnum | TenantUserScalarFieldEnum[]
  }

  /**
   * TenantUser findFirstOrThrow
   */
  export type TenantUserFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    /**
     * Filter, which TenantUser to fetch.
     */
    where?: TenantUserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TenantUsers to fetch.
     */
    orderBy?: TenantUserOrderByWithRelationInput | TenantUserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for TenantUsers.
     */
    cursor?: TenantUserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TenantUsers from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TenantUsers.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of TenantUsers.
     */
    distinct?: TenantUserScalarFieldEnum | TenantUserScalarFieldEnum[]
  }

  /**
   * TenantUser findMany
   */
  export type TenantUserFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    /**
     * Filter, which TenantUsers to fetch.
     */
    where?: TenantUserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TenantUsers to fetch.
     */
    orderBy?: TenantUserOrderByWithRelationInput | TenantUserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing TenantUsers.
     */
    cursor?: TenantUserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TenantUsers from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TenantUsers.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of TenantUsers.
     */
    distinct?: TenantUserScalarFieldEnum | TenantUserScalarFieldEnum[]
  }

  /**
   * TenantUser create
   */
  export type TenantUserCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    /**
     * The data needed to create a TenantUser.
     */
    data: XOR<TenantUserCreateInput, TenantUserUncheckedCreateInput>
  }

  /**
   * TenantUser createMany
   */
  export type TenantUserCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many TenantUsers.
     */
    data: TenantUserCreateManyInput | TenantUserCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * TenantUser createManyAndReturn
   */
  export type TenantUserCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * The data used to create many TenantUsers.
     */
    data: TenantUserCreateManyInput | TenantUserCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * TenantUser update
   */
  export type TenantUserUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    /**
     * The data needed to update a TenantUser.
     */
    data: XOR<TenantUserUpdateInput, TenantUserUncheckedUpdateInput>
    /**
     * Choose, which TenantUser to update.
     */
    where: TenantUserWhereUniqueInput
  }

  /**
   * TenantUser updateMany
   */
  export type TenantUserUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update TenantUsers.
     */
    data: XOR<TenantUserUpdateManyMutationInput, TenantUserUncheckedUpdateManyInput>
    /**
     * Filter which TenantUsers to update
     */
    where?: TenantUserWhereInput
    /**
     * Limit how many TenantUsers to update.
     */
    limit?: number
  }

  /**
   * TenantUser updateManyAndReturn
   */
  export type TenantUserUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * The data used to update TenantUsers.
     */
    data: XOR<TenantUserUpdateManyMutationInput, TenantUserUncheckedUpdateManyInput>
    /**
     * Filter which TenantUsers to update
     */
    where?: TenantUserWhereInput
    /**
     * Limit how many TenantUsers to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * TenantUser upsert
   */
  export type TenantUserUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    /**
     * The filter to search for the TenantUser to update in case it exists.
     */
    where: TenantUserWhereUniqueInput
    /**
     * In case the TenantUser found by the `where` argument doesn't exist, create a new TenantUser with this data.
     */
    create: XOR<TenantUserCreateInput, TenantUserUncheckedCreateInput>
    /**
     * In case the TenantUser was found with the provided `where` argument, update it with this data.
     */
    update: XOR<TenantUserUpdateInput, TenantUserUncheckedUpdateInput>
  }

  /**
   * TenantUser delete
   */
  export type TenantUserDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
    /**
     * Filter which TenantUser to delete.
     */
    where: TenantUserWhereUniqueInput
  }

  /**
   * TenantUser deleteMany
   */
  export type TenantUserDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which TenantUsers to delete
     */
    where?: TenantUserWhereInput
    /**
     * Limit how many TenantUsers to delete.
     */
    limit?: number
  }

  /**
   * TenantUser without action
   */
  export type TenantUserDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantUser
     */
    select?: TenantUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantUser
     */
    omit?: TenantUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantUserInclude<ExtArgs> | null
  }


  /**
   * Model TenantInvite
   */

  export type AggregateTenantInvite = {
    _count: TenantInviteCountAggregateOutputType | null
    _min: TenantInviteMinAggregateOutputType | null
    _max: TenantInviteMaxAggregateOutputType | null
  }

  export type TenantInviteMinAggregateOutputType = {
    id: string | null
    tenantId: string | null
    email: string | null
    role: $Enums.TenantRole | null
    token: string | null
    expiresAt: Date | null
    usedAt: Date | null
    acceptedAt: Date | null
    revokedAt: Date | null
    createdAt: Date | null
  }

  export type TenantInviteMaxAggregateOutputType = {
    id: string | null
    tenantId: string | null
    email: string | null
    role: $Enums.TenantRole | null
    token: string | null
    expiresAt: Date | null
    usedAt: Date | null
    acceptedAt: Date | null
    revokedAt: Date | null
    createdAt: Date | null
  }

  export type TenantInviteCountAggregateOutputType = {
    id: number
    tenantId: number
    email: number
    role: number
    token: number
    expiresAt: number
    usedAt: number
    acceptedAt: number
    revokedAt: number
    createdAt: number
    _all: number
  }


  export type TenantInviteMinAggregateInputType = {
    id?: true
    tenantId?: true
    email?: true
    role?: true
    token?: true
    expiresAt?: true
    usedAt?: true
    acceptedAt?: true
    revokedAt?: true
    createdAt?: true
  }

  export type TenantInviteMaxAggregateInputType = {
    id?: true
    tenantId?: true
    email?: true
    role?: true
    token?: true
    expiresAt?: true
    usedAt?: true
    acceptedAt?: true
    revokedAt?: true
    createdAt?: true
  }

  export type TenantInviteCountAggregateInputType = {
    id?: true
    tenantId?: true
    email?: true
    role?: true
    token?: true
    expiresAt?: true
    usedAt?: true
    acceptedAt?: true
    revokedAt?: true
    createdAt?: true
    _all?: true
  }

  export type TenantInviteAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which TenantInvite to aggregate.
     */
    where?: TenantInviteWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TenantInvites to fetch.
     */
    orderBy?: TenantInviteOrderByWithRelationInput | TenantInviteOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: TenantInviteWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TenantInvites from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TenantInvites.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned TenantInvites
    **/
    _count?: true | TenantInviteCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: TenantInviteMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: TenantInviteMaxAggregateInputType
  }

  export type GetTenantInviteAggregateType<T extends TenantInviteAggregateArgs> = {
        [P in keyof T & keyof AggregateTenantInvite]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateTenantInvite[P]>
      : GetScalarType<T[P], AggregateTenantInvite[P]>
  }




  export type TenantInviteGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TenantInviteWhereInput
    orderBy?: TenantInviteOrderByWithAggregationInput | TenantInviteOrderByWithAggregationInput[]
    by: TenantInviteScalarFieldEnum[] | TenantInviteScalarFieldEnum
    having?: TenantInviteScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: TenantInviteCountAggregateInputType | true
    _min?: TenantInviteMinAggregateInputType
    _max?: TenantInviteMaxAggregateInputType
  }

  export type TenantInviteGroupByOutputType = {
    id: string
    tenantId: string
    email: string
    role: $Enums.TenantRole
    token: string
    expiresAt: Date
    usedAt: Date | null
    acceptedAt: Date | null
    revokedAt: Date | null
    createdAt: Date
    _count: TenantInviteCountAggregateOutputType | null
    _min: TenantInviteMinAggregateOutputType | null
    _max: TenantInviteMaxAggregateOutputType | null
  }

  type GetTenantInviteGroupByPayload<T extends TenantInviteGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<TenantInviteGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof TenantInviteGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], TenantInviteGroupByOutputType[P]>
            : GetScalarType<T[P], TenantInviteGroupByOutputType[P]>
        }
      >
    >


  export type TenantInviteSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    tenantId?: boolean
    email?: boolean
    role?: boolean
    token?: boolean
    expiresAt?: boolean
    usedAt?: boolean
    acceptedAt?: boolean
    revokedAt?: boolean
    createdAt?: boolean
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["tenantInvite"]>

  export type TenantInviteSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    tenantId?: boolean
    email?: boolean
    role?: boolean
    token?: boolean
    expiresAt?: boolean
    usedAt?: boolean
    acceptedAt?: boolean
    revokedAt?: boolean
    createdAt?: boolean
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["tenantInvite"]>

  export type TenantInviteSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    tenantId?: boolean
    email?: boolean
    role?: boolean
    token?: boolean
    expiresAt?: boolean
    usedAt?: boolean
    acceptedAt?: boolean
    revokedAt?: boolean
    createdAt?: boolean
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["tenantInvite"]>

  export type TenantInviteSelectScalar = {
    id?: boolean
    tenantId?: boolean
    email?: boolean
    role?: boolean
    token?: boolean
    expiresAt?: boolean
    usedAt?: boolean
    acceptedAt?: boolean
    revokedAt?: boolean
    createdAt?: boolean
  }

  export type TenantInviteOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "tenantId" | "email" | "role" | "token" | "expiresAt" | "usedAt" | "acceptedAt" | "revokedAt" | "createdAt", ExtArgs["result"]["tenantInvite"]>
  export type TenantInviteInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
    user?: boolean | UserDefaultArgs<ExtArgs>
  }
  export type TenantInviteIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
    user?: boolean | UserDefaultArgs<ExtArgs>
  }
  export type TenantInviteIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
    user?: boolean | UserDefaultArgs<ExtArgs>
  }

  export type $TenantInvitePayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "TenantInvite"
    objects: {
      tenant: Prisma.$TenantPayload<ExtArgs>
      user: Prisma.$UserPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      tenantId: string
      email: string
      role: $Enums.TenantRole
      token: string
      expiresAt: Date
      usedAt: Date | null
      acceptedAt: Date | null
      revokedAt: Date | null
      createdAt: Date
    }, ExtArgs["result"]["tenantInvite"]>
    composites: {}
  }

  type TenantInviteGetPayload<S extends boolean | null | undefined | TenantInviteDefaultArgs> = $Result.GetResult<Prisma.$TenantInvitePayload, S>

  type TenantInviteCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<TenantInviteFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: TenantInviteCountAggregateInputType | true
    }

  export interface TenantInviteDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['TenantInvite'], meta: { name: 'TenantInvite' } }
    /**
     * Find zero or one TenantInvite that matches the filter.
     * @param {TenantInviteFindUniqueArgs} args - Arguments to find a TenantInvite
     * @example
     * // Get one TenantInvite
     * const tenantInvite = await prisma.tenantInvite.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends TenantInviteFindUniqueArgs>(args: SelectSubset<T, TenantInviteFindUniqueArgs<ExtArgs>>): Prisma__TenantInviteClient<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one TenantInvite that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {TenantInviteFindUniqueOrThrowArgs} args - Arguments to find a TenantInvite
     * @example
     * // Get one TenantInvite
     * const tenantInvite = await prisma.tenantInvite.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends TenantInviteFindUniqueOrThrowArgs>(args: SelectSubset<T, TenantInviteFindUniqueOrThrowArgs<ExtArgs>>): Prisma__TenantInviteClient<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first TenantInvite that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantInviteFindFirstArgs} args - Arguments to find a TenantInvite
     * @example
     * // Get one TenantInvite
     * const tenantInvite = await prisma.tenantInvite.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends TenantInviteFindFirstArgs>(args?: SelectSubset<T, TenantInviteFindFirstArgs<ExtArgs>>): Prisma__TenantInviteClient<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first TenantInvite that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantInviteFindFirstOrThrowArgs} args - Arguments to find a TenantInvite
     * @example
     * // Get one TenantInvite
     * const tenantInvite = await prisma.tenantInvite.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends TenantInviteFindFirstOrThrowArgs>(args?: SelectSubset<T, TenantInviteFindFirstOrThrowArgs<ExtArgs>>): Prisma__TenantInviteClient<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more TenantInvites that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantInviteFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all TenantInvites
     * const tenantInvites = await prisma.tenantInvite.findMany()
     * 
     * // Get first 10 TenantInvites
     * const tenantInvites = await prisma.tenantInvite.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const tenantInviteWithIdOnly = await prisma.tenantInvite.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends TenantInviteFindManyArgs>(args?: SelectSubset<T, TenantInviteFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a TenantInvite.
     * @param {TenantInviteCreateArgs} args - Arguments to create a TenantInvite.
     * @example
     * // Create one TenantInvite
     * const TenantInvite = await prisma.tenantInvite.create({
     *   data: {
     *     // ... data to create a TenantInvite
     *   }
     * })
     * 
     */
    create<T extends TenantInviteCreateArgs>(args: SelectSubset<T, TenantInviteCreateArgs<ExtArgs>>): Prisma__TenantInviteClient<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many TenantInvites.
     * @param {TenantInviteCreateManyArgs} args - Arguments to create many TenantInvites.
     * @example
     * // Create many TenantInvites
     * const tenantInvite = await prisma.tenantInvite.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends TenantInviteCreateManyArgs>(args?: SelectSubset<T, TenantInviteCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many TenantInvites and returns the data saved in the database.
     * @param {TenantInviteCreateManyAndReturnArgs} args - Arguments to create many TenantInvites.
     * @example
     * // Create many TenantInvites
     * const tenantInvite = await prisma.tenantInvite.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many TenantInvites and only return the `id`
     * const tenantInviteWithIdOnly = await prisma.tenantInvite.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends TenantInviteCreateManyAndReturnArgs>(args?: SelectSubset<T, TenantInviteCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a TenantInvite.
     * @param {TenantInviteDeleteArgs} args - Arguments to delete one TenantInvite.
     * @example
     * // Delete one TenantInvite
     * const TenantInvite = await prisma.tenantInvite.delete({
     *   where: {
     *     // ... filter to delete one TenantInvite
     *   }
     * })
     * 
     */
    delete<T extends TenantInviteDeleteArgs>(args: SelectSubset<T, TenantInviteDeleteArgs<ExtArgs>>): Prisma__TenantInviteClient<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one TenantInvite.
     * @param {TenantInviteUpdateArgs} args - Arguments to update one TenantInvite.
     * @example
     * // Update one TenantInvite
     * const tenantInvite = await prisma.tenantInvite.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends TenantInviteUpdateArgs>(args: SelectSubset<T, TenantInviteUpdateArgs<ExtArgs>>): Prisma__TenantInviteClient<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more TenantInvites.
     * @param {TenantInviteDeleteManyArgs} args - Arguments to filter TenantInvites to delete.
     * @example
     * // Delete a few TenantInvites
     * const { count } = await prisma.tenantInvite.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends TenantInviteDeleteManyArgs>(args?: SelectSubset<T, TenantInviteDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more TenantInvites.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantInviteUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many TenantInvites
     * const tenantInvite = await prisma.tenantInvite.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends TenantInviteUpdateManyArgs>(args: SelectSubset<T, TenantInviteUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more TenantInvites and returns the data updated in the database.
     * @param {TenantInviteUpdateManyAndReturnArgs} args - Arguments to update many TenantInvites.
     * @example
     * // Update many TenantInvites
     * const tenantInvite = await prisma.tenantInvite.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more TenantInvites and only return the `id`
     * const tenantInviteWithIdOnly = await prisma.tenantInvite.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends TenantInviteUpdateManyAndReturnArgs>(args: SelectSubset<T, TenantInviteUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one TenantInvite.
     * @param {TenantInviteUpsertArgs} args - Arguments to update or create a TenantInvite.
     * @example
     * // Update or create a TenantInvite
     * const tenantInvite = await prisma.tenantInvite.upsert({
     *   create: {
     *     // ... data to create a TenantInvite
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the TenantInvite we want to update
     *   }
     * })
     */
    upsert<T extends TenantInviteUpsertArgs>(args: SelectSubset<T, TenantInviteUpsertArgs<ExtArgs>>): Prisma__TenantInviteClient<$Result.GetResult<Prisma.$TenantInvitePayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of TenantInvites.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantInviteCountArgs} args - Arguments to filter TenantInvites to count.
     * @example
     * // Count the number of TenantInvites
     * const count = await prisma.tenantInvite.count({
     *   where: {
     *     // ... the filter for the TenantInvites we want to count
     *   }
     * })
    **/
    count<T extends TenantInviteCountArgs>(
      args?: Subset<T, TenantInviteCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], TenantInviteCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a TenantInvite.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantInviteAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends TenantInviteAggregateArgs>(args: Subset<T, TenantInviteAggregateArgs>): Prisma.PrismaPromise<GetTenantInviteAggregateType<T>>

    /**
     * Group by TenantInvite.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TenantInviteGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends TenantInviteGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: TenantInviteGroupByArgs['orderBy'] }
        : { orderBy?: TenantInviteGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, TenantInviteGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetTenantInviteGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the TenantInvite model
   */
  readonly fields: TenantInviteFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for TenantInvite.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__TenantInviteClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    tenant<T extends TenantDefaultArgs<ExtArgs> = {}>(args?: Subset<T, TenantDefaultArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    user<T extends UserDefaultArgs<ExtArgs> = {}>(args?: Subset<T, UserDefaultArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the TenantInvite model
   */
  interface TenantInviteFieldRefs {
    readonly id: FieldRef<"TenantInvite", 'String'>
    readonly tenantId: FieldRef<"TenantInvite", 'String'>
    readonly email: FieldRef<"TenantInvite", 'String'>
    readonly role: FieldRef<"TenantInvite", 'TenantRole'>
    readonly token: FieldRef<"TenantInvite", 'String'>
    readonly expiresAt: FieldRef<"TenantInvite", 'DateTime'>
    readonly usedAt: FieldRef<"TenantInvite", 'DateTime'>
    readonly acceptedAt: FieldRef<"TenantInvite", 'DateTime'>
    readonly revokedAt: FieldRef<"TenantInvite", 'DateTime'>
    readonly createdAt: FieldRef<"TenantInvite", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * TenantInvite findUnique
   */
  export type TenantInviteFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    /**
     * Filter, which TenantInvite to fetch.
     */
    where: TenantInviteWhereUniqueInput
  }

  /**
   * TenantInvite findUniqueOrThrow
   */
  export type TenantInviteFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    /**
     * Filter, which TenantInvite to fetch.
     */
    where: TenantInviteWhereUniqueInput
  }

  /**
   * TenantInvite findFirst
   */
  export type TenantInviteFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    /**
     * Filter, which TenantInvite to fetch.
     */
    where?: TenantInviteWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TenantInvites to fetch.
     */
    orderBy?: TenantInviteOrderByWithRelationInput | TenantInviteOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for TenantInvites.
     */
    cursor?: TenantInviteWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TenantInvites from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TenantInvites.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of TenantInvites.
     */
    distinct?: TenantInviteScalarFieldEnum | TenantInviteScalarFieldEnum[]
  }

  /**
   * TenantInvite findFirstOrThrow
   */
  export type TenantInviteFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    /**
     * Filter, which TenantInvite to fetch.
     */
    where?: TenantInviteWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TenantInvites to fetch.
     */
    orderBy?: TenantInviteOrderByWithRelationInput | TenantInviteOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for TenantInvites.
     */
    cursor?: TenantInviteWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TenantInvites from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TenantInvites.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of TenantInvites.
     */
    distinct?: TenantInviteScalarFieldEnum | TenantInviteScalarFieldEnum[]
  }

  /**
   * TenantInvite findMany
   */
  export type TenantInviteFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    /**
     * Filter, which TenantInvites to fetch.
     */
    where?: TenantInviteWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TenantInvites to fetch.
     */
    orderBy?: TenantInviteOrderByWithRelationInput | TenantInviteOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing TenantInvites.
     */
    cursor?: TenantInviteWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TenantInvites from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TenantInvites.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of TenantInvites.
     */
    distinct?: TenantInviteScalarFieldEnum | TenantInviteScalarFieldEnum[]
  }

  /**
   * TenantInvite create
   */
  export type TenantInviteCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    /**
     * The data needed to create a TenantInvite.
     */
    data: XOR<TenantInviteCreateInput, TenantInviteUncheckedCreateInput>
  }

  /**
   * TenantInvite createMany
   */
  export type TenantInviteCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many TenantInvites.
     */
    data: TenantInviteCreateManyInput | TenantInviteCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * TenantInvite createManyAndReturn
   */
  export type TenantInviteCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * The data used to create many TenantInvites.
     */
    data: TenantInviteCreateManyInput | TenantInviteCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * TenantInvite update
   */
  export type TenantInviteUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    /**
     * The data needed to update a TenantInvite.
     */
    data: XOR<TenantInviteUpdateInput, TenantInviteUncheckedUpdateInput>
    /**
     * Choose, which TenantInvite to update.
     */
    where: TenantInviteWhereUniqueInput
  }

  /**
   * TenantInvite updateMany
   */
  export type TenantInviteUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update TenantInvites.
     */
    data: XOR<TenantInviteUpdateManyMutationInput, TenantInviteUncheckedUpdateManyInput>
    /**
     * Filter which TenantInvites to update
     */
    where?: TenantInviteWhereInput
    /**
     * Limit how many TenantInvites to update.
     */
    limit?: number
  }

  /**
   * TenantInvite updateManyAndReturn
   */
  export type TenantInviteUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * The data used to update TenantInvites.
     */
    data: XOR<TenantInviteUpdateManyMutationInput, TenantInviteUncheckedUpdateManyInput>
    /**
     * Filter which TenantInvites to update
     */
    where?: TenantInviteWhereInput
    /**
     * Limit how many TenantInvites to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * TenantInvite upsert
   */
  export type TenantInviteUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    /**
     * The filter to search for the TenantInvite to update in case it exists.
     */
    where: TenantInviteWhereUniqueInput
    /**
     * In case the TenantInvite found by the `where` argument doesn't exist, create a new TenantInvite with this data.
     */
    create: XOR<TenantInviteCreateInput, TenantInviteUncheckedCreateInput>
    /**
     * In case the TenantInvite was found with the provided `where` argument, update it with this data.
     */
    update: XOR<TenantInviteUpdateInput, TenantInviteUncheckedUpdateInput>
  }

  /**
   * TenantInvite delete
   */
  export type TenantInviteDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
    /**
     * Filter which TenantInvite to delete.
     */
    where: TenantInviteWhereUniqueInput
  }

  /**
   * TenantInvite deleteMany
   */
  export type TenantInviteDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which TenantInvites to delete
     */
    where?: TenantInviteWhereInput
    /**
     * Limit how many TenantInvites to delete.
     */
    limit?: number
  }

  /**
   * TenantInvite without action
   */
  export type TenantInviteDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TenantInvite
     */
    select?: TenantInviteSelect<ExtArgs> | null
    /**
     * Omit specific fields from the TenantInvite
     */
    omit?: TenantInviteOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TenantInviteInclude<ExtArgs> | null
  }


  /**
   * Model Session
   */

  export type AggregateSession = {
    _count: SessionCountAggregateOutputType | null
    _min: SessionMinAggregateOutputType | null
    _max: SessionMaxAggregateOutputType | null
  }

  export type SessionMinAggregateOutputType = {
    id: string | null
    userId: string | null
    token: string | null
    expiresAt: Date | null
    createdAt: Date | null
    ipAddress: string | null
    userAgent: string | null
    impersonatingTenantId: string | null
  }

  export type SessionMaxAggregateOutputType = {
    id: string | null
    userId: string | null
    token: string | null
    expiresAt: Date | null
    createdAt: Date | null
    ipAddress: string | null
    userAgent: string | null
    impersonatingTenantId: string | null
  }

  export type SessionCountAggregateOutputType = {
    id: number
    userId: number
    token: number
    expiresAt: number
    createdAt: number
    ipAddress: number
    userAgent: number
    impersonatingTenantId: number
    _all: number
  }


  export type SessionMinAggregateInputType = {
    id?: true
    userId?: true
    token?: true
    expiresAt?: true
    createdAt?: true
    ipAddress?: true
    userAgent?: true
    impersonatingTenantId?: true
  }

  export type SessionMaxAggregateInputType = {
    id?: true
    userId?: true
    token?: true
    expiresAt?: true
    createdAt?: true
    ipAddress?: true
    userAgent?: true
    impersonatingTenantId?: true
  }

  export type SessionCountAggregateInputType = {
    id?: true
    userId?: true
    token?: true
    expiresAt?: true
    createdAt?: true
    ipAddress?: true
    userAgent?: true
    impersonatingTenantId?: true
    _all?: true
  }

  export type SessionAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Session to aggregate.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Sessions
    **/
    _count?: true | SessionCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: SessionMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: SessionMaxAggregateInputType
  }

  export type GetSessionAggregateType<T extends SessionAggregateArgs> = {
        [P in keyof T & keyof AggregateSession]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateSession[P]>
      : GetScalarType<T[P], AggregateSession[P]>
  }




  export type SessionGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: SessionWhereInput
    orderBy?: SessionOrderByWithAggregationInput | SessionOrderByWithAggregationInput[]
    by: SessionScalarFieldEnum[] | SessionScalarFieldEnum
    having?: SessionScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: SessionCountAggregateInputType | true
    _min?: SessionMinAggregateInputType
    _max?: SessionMaxAggregateInputType
  }

  export type SessionGroupByOutputType = {
    id: string
    userId: string
    token: string
    expiresAt: Date
    createdAt: Date
    ipAddress: string | null
    userAgent: string | null
    impersonatingTenantId: string | null
    _count: SessionCountAggregateOutputType | null
    _min: SessionMinAggregateOutputType | null
    _max: SessionMaxAggregateOutputType | null
  }

  type GetSessionGroupByPayload<T extends SessionGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<SessionGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof SessionGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], SessionGroupByOutputType[P]>
            : GetScalarType<T[P], SessionGroupByOutputType[P]>
        }
      >
    >


  export type SessionSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    token?: boolean
    expiresAt?: boolean
    createdAt?: boolean
    ipAddress?: boolean
    userAgent?: boolean
    impersonatingTenantId?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["session"]>

  export type SessionSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    token?: boolean
    expiresAt?: boolean
    createdAt?: boolean
    ipAddress?: boolean
    userAgent?: boolean
    impersonatingTenantId?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["session"]>

  export type SessionSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    token?: boolean
    expiresAt?: boolean
    createdAt?: boolean
    ipAddress?: boolean
    userAgent?: boolean
    impersonatingTenantId?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["session"]>

  export type SessionSelectScalar = {
    id?: boolean
    userId?: boolean
    token?: boolean
    expiresAt?: boolean
    createdAt?: boolean
    ipAddress?: boolean
    userAgent?: boolean
    impersonatingTenantId?: boolean
  }

  export type SessionOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "userId" | "token" | "expiresAt" | "createdAt" | "ipAddress" | "userAgent" | "impersonatingTenantId", ExtArgs["result"]["session"]>
  export type SessionInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }
  export type SessionIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }
  export type SessionIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }

  export type $SessionPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Session"
    objects: {
      user: Prisma.$UserPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      userId: string
      token: string
      expiresAt: Date
      createdAt: Date
      ipAddress: string | null
      userAgent: string | null
      /**
       * When set, the super admin is viewing/acting on behalf of this tenant.
       * This is NOT true impersonation — the session still belongs to the super admin.
       */
      impersonatingTenantId: string | null
    }, ExtArgs["result"]["session"]>
    composites: {}
  }

  type SessionGetPayload<S extends boolean | null | undefined | SessionDefaultArgs> = $Result.GetResult<Prisma.$SessionPayload, S>

  type SessionCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<SessionFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: SessionCountAggregateInputType | true
    }

  export interface SessionDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Session'], meta: { name: 'Session' } }
    /**
     * Find zero or one Session that matches the filter.
     * @param {SessionFindUniqueArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends SessionFindUniqueArgs>(args: SelectSubset<T, SessionFindUniqueArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Session that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {SessionFindUniqueOrThrowArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends SessionFindUniqueOrThrowArgs>(args: SelectSubset<T, SessionFindUniqueOrThrowArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Session that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionFindFirstArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends SessionFindFirstArgs>(args?: SelectSubset<T, SessionFindFirstArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Session that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionFindFirstOrThrowArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends SessionFindFirstOrThrowArgs>(args?: SelectSubset<T, SessionFindFirstOrThrowArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Sessions that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Sessions
     * const sessions = await prisma.session.findMany()
     * 
     * // Get first 10 Sessions
     * const sessions = await prisma.session.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const sessionWithIdOnly = await prisma.session.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends SessionFindManyArgs>(args?: SelectSubset<T, SessionFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Session.
     * @param {SessionCreateArgs} args - Arguments to create a Session.
     * @example
     * // Create one Session
     * const Session = await prisma.session.create({
     *   data: {
     *     // ... data to create a Session
     *   }
     * })
     * 
     */
    create<T extends SessionCreateArgs>(args: SelectSubset<T, SessionCreateArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Sessions.
     * @param {SessionCreateManyArgs} args - Arguments to create many Sessions.
     * @example
     * // Create many Sessions
     * const session = await prisma.session.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends SessionCreateManyArgs>(args?: SelectSubset<T, SessionCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Sessions and returns the data saved in the database.
     * @param {SessionCreateManyAndReturnArgs} args - Arguments to create many Sessions.
     * @example
     * // Create many Sessions
     * const session = await prisma.session.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Sessions and only return the `id`
     * const sessionWithIdOnly = await prisma.session.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends SessionCreateManyAndReturnArgs>(args?: SelectSubset<T, SessionCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Session.
     * @param {SessionDeleteArgs} args - Arguments to delete one Session.
     * @example
     * // Delete one Session
     * const Session = await prisma.session.delete({
     *   where: {
     *     // ... filter to delete one Session
     *   }
     * })
     * 
     */
    delete<T extends SessionDeleteArgs>(args: SelectSubset<T, SessionDeleteArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Session.
     * @param {SessionUpdateArgs} args - Arguments to update one Session.
     * @example
     * // Update one Session
     * const session = await prisma.session.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends SessionUpdateArgs>(args: SelectSubset<T, SessionUpdateArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Sessions.
     * @param {SessionDeleteManyArgs} args - Arguments to filter Sessions to delete.
     * @example
     * // Delete a few Sessions
     * const { count } = await prisma.session.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends SessionDeleteManyArgs>(args?: SelectSubset<T, SessionDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Sessions.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Sessions
     * const session = await prisma.session.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends SessionUpdateManyArgs>(args: SelectSubset<T, SessionUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Sessions and returns the data updated in the database.
     * @param {SessionUpdateManyAndReturnArgs} args - Arguments to update many Sessions.
     * @example
     * // Update many Sessions
     * const session = await prisma.session.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Sessions and only return the `id`
     * const sessionWithIdOnly = await prisma.session.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends SessionUpdateManyAndReturnArgs>(args: SelectSubset<T, SessionUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Session.
     * @param {SessionUpsertArgs} args - Arguments to update or create a Session.
     * @example
     * // Update or create a Session
     * const session = await prisma.session.upsert({
     *   create: {
     *     // ... data to create a Session
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Session we want to update
     *   }
     * })
     */
    upsert<T extends SessionUpsertArgs>(args: SelectSubset<T, SessionUpsertArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Sessions.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionCountArgs} args - Arguments to filter Sessions to count.
     * @example
     * // Count the number of Sessions
     * const count = await prisma.session.count({
     *   where: {
     *     // ... the filter for the Sessions we want to count
     *   }
     * })
    **/
    count<T extends SessionCountArgs>(
      args?: Subset<T, SessionCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], SessionCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Session.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends SessionAggregateArgs>(args: Subset<T, SessionAggregateArgs>): Prisma.PrismaPromise<GetSessionAggregateType<T>>

    /**
     * Group by Session.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends SessionGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: SessionGroupByArgs['orderBy'] }
        : { orderBy?: SessionGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, SessionGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetSessionGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Session model
   */
  readonly fields: SessionFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Session.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__SessionClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    user<T extends UserDefaultArgs<ExtArgs> = {}>(args?: Subset<T, UserDefaultArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Session model
   */
  interface SessionFieldRefs {
    readonly id: FieldRef<"Session", 'String'>
    readonly userId: FieldRef<"Session", 'String'>
    readonly token: FieldRef<"Session", 'String'>
    readonly expiresAt: FieldRef<"Session", 'DateTime'>
    readonly createdAt: FieldRef<"Session", 'DateTime'>
    readonly ipAddress: FieldRef<"Session", 'String'>
    readonly userAgent: FieldRef<"Session", 'String'>
    readonly impersonatingTenantId: FieldRef<"Session", 'String'>
  }
    

  // Custom InputTypes
  /**
   * Session findUnique
   */
  export type SessionFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session findUniqueOrThrow
   */
  export type SessionFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session findFirst
   */
  export type SessionFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Sessions.
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Sessions.
     */
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * Session findFirstOrThrow
   */
  export type SessionFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Sessions.
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Sessions.
     */
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * Session findMany
   */
  export type SessionFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Sessions to fetch.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Sessions.
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Sessions.
     */
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * Session create
   */
  export type SessionCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * The data needed to create a Session.
     */
    data: XOR<SessionCreateInput, SessionUncheckedCreateInput>
  }

  /**
   * Session createMany
   */
  export type SessionCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Sessions.
     */
    data: SessionCreateManyInput | SessionCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Session createManyAndReturn
   */
  export type SessionCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * The data used to create many Sessions.
     */
    data: SessionCreateManyInput | SessionCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Session update
   */
  export type SessionUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * The data needed to update a Session.
     */
    data: XOR<SessionUpdateInput, SessionUncheckedUpdateInput>
    /**
     * Choose, which Session to update.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session updateMany
   */
  export type SessionUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Sessions.
     */
    data: XOR<SessionUpdateManyMutationInput, SessionUncheckedUpdateManyInput>
    /**
     * Filter which Sessions to update
     */
    where?: SessionWhereInput
    /**
     * Limit how many Sessions to update.
     */
    limit?: number
  }

  /**
   * Session updateManyAndReturn
   */
  export type SessionUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * The data used to update Sessions.
     */
    data: XOR<SessionUpdateManyMutationInput, SessionUncheckedUpdateManyInput>
    /**
     * Filter which Sessions to update
     */
    where?: SessionWhereInput
    /**
     * Limit how many Sessions to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Session upsert
   */
  export type SessionUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * The filter to search for the Session to update in case it exists.
     */
    where: SessionWhereUniqueInput
    /**
     * In case the Session found by the `where` argument doesn't exist, create a new Session with this data.
     */
    create: XOR<SessionCreateInput, SessionUncheckedCreateInput>
    /**
     * In case the Session was found with the provided `where` argument, update it with this data.
     */
    update: XOR<SessionUpdateInput, SessionUncheckedUpdateInput>
  }

  /**
   * Session delete
   */
  export type SessionDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter which Session to delete.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session deleteMany
   */
  export type SessionDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Sessions to delete
     */
    where?: SessionWhereInput
    /**
     * Limit how many Sessions to delete.
     */
    limit?: number
  }

  /**
   * Session without action
   */
  export type SessionDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
  }


  /**
   * Model MagicLink
   */

  export type AggregateMagicLink = {
    _count: MagicLinkCountAggregateOutputType | null
    _min: MagicLinkMinAggregateOutputType | null
    _max: MagicLinkMaxAggregateOutputType | null
  }

  export type MagicLinkMinAggregateOutputType = {
    id: string | null
    userId: string | null
    token: string | null
    pollingToken: string | null
    code: string | null
    ipAddress: string | null
    expiresAt: Date | null
    usedAt: Date | null
    createdAt: Date | null
  }

  export type MagicLinkMaxAggregateOutputType = {
    id: string | null
    userId: string | null
    token: string | null
    pollingToken: string | null
    code: string | null
    ipAddress: string | null
    expiresAt: Date | null
    usedAt: Date | null
    createdAt: Date | null
  }

  export type MagicLinkCountAggregateOutputType = {
    id: number
    userId: number
    token: number
    pollingToken: number
    code: number
    ipAddress: number
    expiresAt: number
    usedAt: number
    createdAt: number
    _all: number
  }


  export type MagicLinkMinAggregateInputType = {
    id?: true
    userId?: true
    token?: true
    pollingToken?: true
    code?: true
    ipAddress?: true
    expiresAt?: true
    usedAt?: true
    createdAt?: true
  }

  export type MagicLinkMaxAggregateInputType = {
    id?: true
    userId?: true
    token?: true
    pollingToken?: true
    code?: true
    ipAddress?: true
    expiresAt?: true
    usedAt?: true
    createdAt?: true
  }

  export type MagicLinkCountAggregateInputType = {
    id?: true
    userId?: true
    token?: true
    pollingToken?: true
    code?: true
    ipAddress?: true
    expiresAt?: true
    usedAt?: true
    createdAt?: true
    _all?: true
  }

  export type MagicLinkAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which MagicLink to aggregate.
     */
    where?: MagicLinkWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of MagicLinks to fetch.
     */
    orderBy?: MagicLinkOrderByWithRelationInput | MagicLinkOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: MagicLinkWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` MagicLinks from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` MagicLinks.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned MagicLinks
    **/
    _count?: true | MagicLinkCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: MagicLinkMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: MagicLinkMaxAggregateInputType
  }

  export type GetMagicLinkAggregateType<T extends MagicLinkAggregateArgs> = {
        [P in keyof T & keyof AggregateMagicLink]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateMagicLink[P]>
      : GetScalarType<T[P], AggregateMagicLink[P]>
  }




  export type MagicLinkGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: MagicLinkWhereInput
    orderBy?: MagicLinkOrderByWithAggregationInput | MagicLinkOrderByWithAggregationInput[]
    by: MagicLinkScalarFieldEnum[] | MagicLinkScalarFieldEnum
    having?: MagicLinkScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: MagicLinkCountAggregateInputType | true
    _min?: MagicLinkMinAggregateInputType
    _max?: MagicLinkMaxAggregateInputType
  }

  export type MagicLinkGroupByOutputType = {
    id: string
    userId: string
    token: string
    pollingToken: string | null
    code: string | null
    ipAddress: string | null
    expiresAt: Date
    usedAt: Date | null
    createdAt: Date
    _count: MagicLinkCountAggregateOutputType | null
    _min: MagicLinkMinAggregateOutputType | null
    _max: MagicLinkMaxAggregateOutputType | null
  }

  type GetMagicLinkGroupByPayload<T extends MagicLinkGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<MagicLinkGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof MagicLinkGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], MagicLinkGroupByOutputType[P]>
            : GetScalarType<T[P], MagicLinkGroupByOutputType[P]>
        }
      >
    >


  export type MagicLinkSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    token?: boolean
    pollingToken?: boolean
    code?: boolean
    ipAddress?: boolean
    expiresAt?: boolean
    usedAt?: boolean
    createdAt?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["magicLink"]>

  export type MagicLinkSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    token?: boolean
    pollingToken?: boolean
    code?: boolean
    ipAddress?: boolean
    expiresAt?: boolean
    usedAt?: boolean
    createdAt?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["magicLink"]>

  export type MagicLinkSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    token?: boolean
    pollingToken?: boolean
    code?: boolean
    ipAddress?: boolean
    expiresAt?: boolean
    usedAt?: boolean
    createdAt?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["magicLink"]>

  export type MagicLinkSelectScalar = {
    id?: boolean
    userId?: boolean
    token?: boolean
    pollingToken?: boolean
    code?: boolean
    ipAddress?: boolean
    expiresAt?: boolean
    usedAt?: boolean
    createdAt?: boolean
  }

  export type MagicLinkOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "userId" | "token" | "pollingToken" | "code" | "ipAddress" | "expiresAt" | "usedAt" | "createdAt", ExtArgs["result"]["magicLink"]>
  export type MagicLinkInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }
  export type MagicLinkIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }
  export type MagicLinkIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }

  export type $MagicLinkPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "MagicLink"
    objects: {
      user: Prisma.$UserPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      userId: string
      token: string
      pollingToken: string | null
      code: string | null
      ipAddress: string | null
      expiresAt: Date
      usedAt: Date | null
      createdAt: Date
    }, ExtArgs["result"]["magicLink"]>
    composites: {}
  }

  type MagicLinkGetPayload<S extends boolean | null | undefined | MagicLinkDefaultArgs> = $Result.GetResult<Prisma.$MagicLinkPayload, S>

  type MagicLinkCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<MagicLinkFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: MagicLinkCountAggregateInputType | true
    }

  export interface MagicLinkDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['MagicLink'], meta: { name: 'MagicLink' } }
    /**
     * Find zero or one MagicLink that matches the filter.
     * @param {MagicLinkFindUniqueArgs} args - Arguments to find a MagicLink
     * @example
     * // Get one MagicLink
     * const magicLink = await prisma.magicLink.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends MagicLinkFindUniqueArgs>(args: SelectSubset<T, MagicLinkFindUniqueArgs<ExtArgs>>): Prisma__MagicLinkClient<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one MagicLink that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {MagicLinkFindUniqueOrThrowArgs} args - Arguments to find a MagicLink
     * @example
     * // Get one MagicLink
     * const magicLink = await prisma.magicLink.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends MagicLinkFindUniqueOrThrowArgs>(args: SelectSubset<T, MagicLinkFindUniqueOrThrowArgs<ExtArgs>>): Prisma__MagicLinkClient<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first MagicLink that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MagicLinkFindFirstArgs} args - Arguments to find a MagicLink
     * @example
     * // Get one MagicLink
     * const magicLink = await prisma.magicLink.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends MagicLinkFindFirstArgs>(args?: SelectSubset<T, MagicLinkFindFirstArgs<ExtArgs>>): Prisma__MagicLinkClient<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first MagicLink that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MagicLinkFindFirstOrThrowArgs} args - Arguments to find a MagicLink
     * @example
     * // Get one MagicLink
     * const magicLink = await prisma.magicLink.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends MagicLinkFindFirstOrThrowArgs>(args?: SelectSubset<T, MagicLinkFindFirstOrThrowArgs<ExtArgs>>): Prisma__MagicLinkClient<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more MagicLinks that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MagicLinkFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all MagicLinks
     * const magicLinks = await prisma.magicLink.findMany()
     * 
     * // Get first 10 MagicLinks
     * const magicLinks = await prisma.magicLink.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const magicLinkWithIdOnly = await prisma.magicLink.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends MagicLinkFindManyArgs>(args?: SelectSubset<T, MagicLinkFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a MagicLink.
     * @param {MagicLinkCreateArgs} args - Arguments to create a MagicLink.
     * @example
     * // Create one MagicLink
     * const MagicLink = await prisma.magicLink.create({
     *   data: {
     *     // ... data to create a MagicLink
     *   }
     * })
     * 
     */
    create<T extends MagicLinkCreateArgs>(args: SelectSubset<T, MagicLinkCreateArgs<ExtArgs>>): Prisma__MagicLinkClient<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many MagicLinks.
     * @param {MagicLinkCreateManyArgs} args - Arguments to create many MagicLinks.
     * @example
     * // Create many MagicLinks
     * const magicLink = await prisma.magicLink.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends MagicLinkCreateManyArgs>(args?: SelectSubset<T, MagicLinkCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many MagicLinks and returns the data saved in the database.
     * @param {MagicLinkCreateManyAndReturnArgs} args - Arguments to create many MagicLinks.
     * @example
     * // Create many MagicLinks
     * const magicLink = await prisma.magicLink.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many MagicLinks and only return the `id`
     * const magicLinkWithIdOnly = await prisma.magicLink.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends MagicLinkCreateManyAndReturnArgs>(args?: SelectSubset<T, MagicLinkCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a MagicLink.
     * @param {MagicLinkDeleteArgs} args - Arguments to delete one MagicLink.
     * @example
     * // Delete one MagicLink
     * const MagicLink = await prisma.magicLink.delete({
     *   where: {
     *     // ... filter to delete one MagicLink
     *   }
     * })
     * 
     */
    delete<T extends MagicLinkDeleteArgs>(args: SelectSubset<T, MagicLinkDeleteArgs<ExtArgs>>): Prisma__MagicLinkClient<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one MagicLink.
     * @param {MagicLinkUpdateArgs} args - Arguments to update one MagicLink.
     * @example
     * // Update one MagicLink
     * const magicLink = await prisma.magicLink.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends MagicLinkUpdateArgs>(args: SelectSubset<T, MagicLinkUpdateArgs<ExtArgs>>): Prisma__MagicLinkClient<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more MagicLinks.
     * @param {MagicLinkDeleteManyArgs} args - Arguments to filter MagicLinks to delete.
     * @example
     * // Delete a few MagicLinks
     * const { count } = await prisma.magicLink.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends MagicLinkDeleteManyArgs>(args?: SelectSubset<T, MagicLinkDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more MagicLinks.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MagicLinkUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many MagicLinks
     * const magicLink = await prisma.magicLink.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends MagicLinkUpdateManyArgs>(args: SelectSubset<T, MagicLinkUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more MagicLinks and returns the data updated in the database.
     * @param {MagicLinkUpdateManyAndReturnArgs} args - Arguments to update many MagicLinks.
     * @example
     * // Update many MagicLinks
     * const magicLink = await prisma.magicLink.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more MagicLinks and only return the `id`
     * const magicLinkWithIdOnly = await prisma.magicLink.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends MagicLinkUpdateManyAndReturnArgs>(args: SelectSubset<T, MagicLinkUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one MagicLink.
     * @param {MagicLinkUpsertArgs} args - Arguments to update or create a MagicLink.
     * @example
     * // Update or create a MagicLink
     * const magicLink = await prisma.magicLink.upsert({
     *   create: {
     *     // ... data to create a MagicLink
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the MagicLink we want to update
     *   }
     * })
     */
    upsert<T extends MagicLinkUpsertArgs>(args: SelectSubset<T, MagicLinkUpsertArgs<ExtArgs>>): Prisma__MagicLinkClient<$Result.GetResult<Prisma.$MagicLinkPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of MagicLinks.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MagicLinkCountArgs} args - Arguments to filter MagicLinks to count.
     * @example
     * // Count the number of MagicLinks
     * const count = await prisma.magicLink.count({
     *   where: {
     *     // ... the filter for the MagicLinks we want to count
     *   }
     * })
    **/
    count<T extends MagicLinkCountArgs>(
      args?: Subset<T, MagicLinkCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], MagicLinkCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a MagicLink.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MagicLinkAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends MagicLinkAggregateArgs>(args: Subset<T, MagicLinkAggregateArgs>): Prisma.PrismaPromise<GetMagicLinkAggregateType<T>>

    /**
     * Group by MagicLink.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MagicLinkGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends MagicLinkGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: MagicLinkGroupByArgs['orderBy'] }
        : { orderBy?: MagicLinkGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, MagicLinkGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetMagicLinkGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the MagicLink model
   */
  readonly fields: MagicLinkFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for MagicLink.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__MagicLinkClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    user<T extends UserDefaultArgs<ExtArgs> = {}>(args?: Subset<T, UserDefaultArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the MagicLink model
   */
  interface MagicLinkFieldRefs {
    readonly id: FieldRef<"MagicLink", 'String'>
    readonly userId: FieldRef<"MagicLink", 'String'>
    readonly token: FieldRef<"MagicLink", 'String'>
    readonly pollingToken: FieldRef<"MagicLink", 'String'>
    readonly code: FieldRef<"MagicLink", 'String'>
    readonly ipAddress: FieldRef<"MagicLink", 'String'>
    readonly expiresAt: FieldRef<"MagicLink", 'DateTime'>
    readonly usedAt: FieldRef<"MagicLink", 'DateTime'>
    readonly createdAt: FieldRef<"MagicLink", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * MagicLink findUnique
   */
  export type MagicLinkFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
    /**
     * Filter, which MagicLink to fetch.
     */
    where: MagicLinkWhereUniqueInput
  }

  /**
   * MagicLink findUniqueOrThrow
   */
  export type MagicLinkFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
    /**
     * Filter, which MagicLink to fetch.
     */
    where: MagicLinkWhereUniqueInput
  }

  /**
   * MagicLink findFirst
   */
  export type MagicLinkFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
    /**
     * Filter, which MagicLink to fetch.
     */
    where?: MagicLinkWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of MagicLinks to fetch.
     */
    orderBy?: MagicLinkOrderByWithRelationInput | MagicLinkOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for MagicLinks.
     */
    cursor?: MagicLinkWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` MagicLinks from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` MagicLinks.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of MagicLinks.
     */
    distinct?: MagicLinkScalarFieldEnum | MagicLinkScalarFieldEnum[]
  }

  /**
   * MagicLink findFirstOrThrow
   */
  export type MagicLinkFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
    /**
     * Filter, which MagicLink to fetch.
     */
    where?: MagicLinkWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of MagicLinks to fetch.
     */
    orderBy?: MagicLinkOrderByWithRelationInput | MagicLinkOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for MagicLinks.
     */
    cursor?: MagicLinkWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` MagicLinks from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` MagicLinks.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of MagicLinks.
     */
    distinct?: MagicLinkScalarFieldEnum | MagicLinkScalarFieldEnum[]
  }

  /**
   * MagicLink findMany
   */
  export type MagicLinkFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
    /**
     * Filter, which MagicLinks to fetch.
     */
    where?: MagicLinkWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of MagicLinks to fetch.
     */
    orderBy?: MagicLinkOrderByWithRelationInput | MagicLinkOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing MagicLinks.
     */
    cursor?: MagicLinkWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` MagicLinks from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` MagicLinks.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of MagicLinks.
     */
    distinct?: MagicLinkScalarFieldEnum | MagicLinkScalarFieldEnum[]
  }

  /**
   * MagicLink create
   */
  export type MagicLinkCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
    /**
     * The data needed to create a MagicLink.
     */
    data: XOR<MagicLinkCreateInput, MagicLinkUncheckedCreateInput>
  }

  /**
   * MagicLink createMany
   */
  export type MagicLinkCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many MagicLinks.
     */
    data: MagicLinkCreateManyInput | MagicLinkCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * MagicLink createManyAndReturn
   */
  export type MagicLinkCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * The data used to create many MagicLinks.
     */
    data: MagicLinkCreateManyInput | MagicLinkCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * MagicLink update
   */
  export type MagicLinkUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
    /**
     * The data needed to update a MagicLink.
     */
    data: XOR<MagicLinkUpdateInput, MagicLinkUncheckedUpdateInput>
    /**
     * Choose, which MagicLink to update.
     */
    where: MagicLinkWhereUniqueInput
  }

  /**
   * MagicLink updateMany
   */
  export type MagicLinkUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update MagicLinks.
     */
    data: XOR<MagicLinkUpdateManyMutationInput, MagicLinkUncheckedUpdateManyInput>
    /**
     * Filter which MagicLinks to update
     */
    where?: MagicLinkWhereInput
    /**
     * Limit how many MagicLinks to update.
     */
    limit?: number
  }

  /**
   * MagicLink updateManyAndReturn
   */
  export type MagicLinkUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * The data used to update MagicLinks.
     */
    data: XOR<MagicLinkUpdateManyMutationInput, MagicLinkUncheckedUpdateManyInput>
    /**
     * Filter which MagicLinks to update
     */
    where?: MagicLinkWhereInput
    /**
     * Limit how many MagicLinks to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * MagicLink upsert
   */
  export type MagicLinkUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
    /**
     * The filter to search for the MagicLink to update in case it exists.
     */
    where: MagicLinkWhereUniqueInput
    /**
     * In case the MagicLink found by the `where` argument doesn't exist, create a new MagicLink with this data.
     */
    create: XOR<MagicLinkCreateInput, MagicLinkUncheckedCreateInput>
    /**
     * In case the MagicLink was found with the provided `where` argument, update it with this data.
     */
    update: XOR<MagicLinkUpdateInput, MagicLinkUncheckedUpdateInput>
  }

  /**
   * MagicLink delete
   */
  export type MagicLinkDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
    /**
     * Filter which MagicLink to delete.
     */
    where: MagicLinkWhereUniqueInput
  }

  /**
   * MagicLink deleteMany
   */
  export type MagicLinkDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which MagicLinks to delete
     */
    where?: MagicLinkWhereInput
    /**
     * Limit how many MagicLinks to delete.
     */
    limit?: number
  }

  /**
   * MagicLink without action
   */
  export type MagicLinkDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MagicLink
     */
    select?: MagicLinkSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MagicLink
     */
    omit?: MagicLinkOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MagicLinkInclude<ExtArgs> | null
  }


  /**
   * Model AppSettings
   */

  export type AggregateAppSettings = {
    _count: AppSettingsCountAggregateOutputType | null
    _min: AppSettingsMinAggregateOutputType | null
    _max: AppSettingsMaxAggregateOutputType | null
  }

  export type AppSettingsMinAggregateOutputType = {
    id: string | null
    brandName: string | null
    brandLogoUrl: string | null
    brandLogoUrlDark: string | null
    brandTagline: string | null
    customCss: string | null
    primaryColor: string | null
    accentColor: string | null
    emailButtonColor: string | null
    loginBgColor: string | null
    loginCardColor: string | null
    loginTextColor: string | null
    loginInputColor: string | null
    loginRingColor: string | null
    loginBgColorDark: string | null
    loginCardColorDark: string | null
    loginTextColorDark: string | null
    loginInputColorDark: string | null
    loginRingColorDark: string | null
    sidebarBgColor: string | null
    sidebarTextColor: string | null
    sidebarAccentColor: string | null
    faviconUrl: string | null
    loginHeading: string | null
    loginSubheading: string | null
    disabledPlugins: string | null
    updatedAt: Date | null
  }

  export type AppSettingsMaxAggregateOutputType = {
    id: string | null
    brandName: string | null
    brandLogoUrl: string | null
    brandLogoUrlDark: string | null
    brandTagline: string | null
    customCss: string | null
    primaryColor: string | null
    accentColor: string | null
    emailButtonColor: string | null
    loginBgColor: string | null
    loginCardColor: string | null
    loginTextColor: string | null
    loginInputColor: string | null
    loginRingColor: string | null
    loginBgColorDark: string | null
    loginCardColorDark: string | null
    loginTextColorDark: string | null
    loginInputColorDark: string | null
    loginRingColorDark: string | null
    sidebarBgColor: string | null
    sidebarTextColor: string | null
    sidebarAccentColor: string | null
    faviconUrl: string | null
    loginHeading: string | null
    loginSubheading: string | null
    disabledPlugins: string | null
    updatedAt: Date | null
  }

  export type AppSettingsCountAggregateOutputType = {
    id: number
    brandName: number
    brandLogoUrl: number
    brandLogoUrlDark: number
    brandTagline: number
    customCss: number
    primaryColor: number
    accentColor: number
    emailButtonColor: number
    loginBgColor: number
    loginCardColor: number
    loginTextColor: number
    loginInputColor: number
    loginRingColor: number
    loginBgColorDark: number
    loginCardColorDark: number
    loginTextColorDark: number
    loginInputColorDark: number
    loginRingColorDark: number
    sidebarBgColor: number
    sidebarTextColor: number
    sidebarAccentColor: number
    faviconUrl: number
    loginHeading: number
    loginSubheading: number
    disabledPlugins: number
    updatedAt: number
    _all: number
  }


  export type AppSettingsMinAggregateInputType = {
    id?: true
    brandName?: true
    brandLogoUrl?: true
    brandLogoUrlDark?: true
    brandTagline?: true
    customCss?: true
    primaryColor?: true
    accentColor?: true
    emailButtonColor?: true
    loginBgColor?: true
    loginCardColor?: true
    loginTextColor?: true
    loginInputColor?: true
    loginRingColor?: true
    loginBgColorDark?: true
    loginCardColorDark?: true
    loginTextColorDark?: true
    loginInputColorDark?: true
    loginRingColorDark?: true
    sidebarBgColor?: true
    sidebarTextColor?: true
    sidebarAccentColor?: true
    faviconUrl?: true
    loginHeading?: true
    loginSubheading?: true
    disabledPlugins?: true
    updatedAt?: true
  }

  export type AppSettingsMaxAggregateInputType = {
    id?: true
    brandName?: true
    brandLogoUrl?: true
    brandLogoUrlDark?: true
    brandTagline?: true
    customCss?: true
    primaryColor?: true
    accentColor?: true
    emailButtonColor?: true
    loginBgColor?: true
    loginCardColor?: true
    loginTextColor?: true
    loginInputColor?: true
    loginRingColor?: true
    loginBgColorDark?: true
    loginCardColorDark?: true
    loginTextColorDark?: true
    loginInputColorDark?: true
    loginRingColorDark?: true
    sidebarBgColor?: true
    sidebarTextColor?: true
    sidebarAccentColor?: true
    faviconUrl?: true
    loginHeading?: true
    loginSubheading?: true
    disabledPlugins?: true
    updatedAt?: true
  }

  export type AppSettingsCountAggregateInputType = {
    id?: true
    brandName?: true
    brandLogoUrl?: true
    brandLogoUrlDark?: true
    brandTagline?: true
    customCss?: true
    primaryColor?: true
    accentColor?: true
    emailButtonColor?: true
    loginBgColor?: true
    loginCardColor?: true
    loginTextColor?: true
    loginInputColor?: true
    loginRingColor?: true
    loginBgColorDark?: true
    loginCardColorDark?: true
    loginTextColorDark?: true
    loginInputColorDark?: true
    loginRingColorDark?: true
    sidebarBgColor?: true
    sidebarTextColor?: true
    sidebarAccentColor?: true
    faviconUrl?: true
    loginHeading?: true
    loginSubheading?: true
    disabledPlugins?: true
    updatedAt?: true
    _all?: true
  }

  export type AppSettingsAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which AppSettings to aggregate.
     */
    where?: AppSettingsWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AppSettings to fetch.
     */
    orderBy?: AppSettingsOrderByWithRelationInput | AppSettingsOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: AppSettingsWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AppSettings from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AppSettings.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned AppSettings
    **/
    _count?: true | AppSettingsCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: AppSettingsMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: AppSettingsMaxAggregateInputType
  }

  export type GetAppSettingsAggregateType<T extends AppSettingsAggregateArgs> = {
        [P in keyof T & keyof AggregateAppSettings]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateAppSettings[P]>
      : GetScalarType<T[P], AggregateAppSettings[P]>
  }




  export type AppSettingsGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: AppSettingsWhereInput
    orderBy?: AppSettingsOrderByWithAggregationInput | AppSettingsOrderByWithAggregationInput[]
    by: AppSettingsScalarFieldEnum[] | AppSettingsScalarFieldEnum
    having?: AppSettingsScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: AppSettingsCountAggregateInputType | true
    _min?: AppSettingsMinAggregateInputType
    _max?: AppSettingsMaxAggregateInputType
  }

  export type AppSettingsGroupByOutputType = {
    id: string
    brandName: string | null
    brandLogoUrl: string | null
    brandLogoUrlDark: string | null
    brandTagline: string | null
    customCss: string | null
    primaryColor: string | null
    accentColor: string | null
    emailButtonColor: string | null
    loginBgColor: string | null
    loginCardColor: string | null
    loginTextColor: string | null
    loginInputColor: string | null
    loginRingColor: string | null
    loginBgColorDark: string | null
    loginCardColorDark: string | null
    loginTextColorDark: string | null
    loginInputColorDark: string | null
    loginRingColorDark: string | null
    sidebarBgColor: string | null
    sidebarTextColor: string | null
    sidebarAccentColor: string | null
    faviconUrl: string | null
    loginHeading: string | null
    loginSubheading: string | null
    disabledPlugins: string | null
    updatedAt: Date
    _count: AppSettingsCountAggregateOutputType | null
    _min: AppSettingsMinAggregateOutputType | null
    _max: AppSettingsMaxAggregateOutputType | null
  }

  type GetAppSettingsGroupByPayload<T extends AppSettingsGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<AppSettingsGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof AppSettingsGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], AppSettingsGroupByOutputType[P]>
            : GetScalarType<T[P], AppSettingsGroupByOutputType[P]>
        }
      >
    >


  export type AppSettingsSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    brandName?: boolean
    brandLogoUrl?: boolean
    brandLogoUrlDark?: boolean
    brandTagline?: boolean
    customCss?: boolean
    primaryColor?: boolean
    accentColor?: boolean
    emailButtonColor?: boolean
    loginBgColor?: boolean
    loginCardColor?: boolean
    loginTextColor?: boolean
    loginInputColor?: boolean
    loginRingColor?: boolean
    loginBgColorDark?: boolean
    loginCardColorDark?: boolean
    loginTextColorDark?: boolean
    loginInputColorDark?: boolean
    loginRingColorDark?: boolean
    sidebarBgColor?: boolean
    sidebarTextColor?: boolean
    sidebarAccentColor?: boolean
    faviconUrl?: boolean
    loginHeading?: boolean
    loginSubheading?: boolean
    disabledPlugins?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["appSettings"]>

  export type AppSettingsSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    brandName?: boolean
    brandLogoUrl?: boolean
    brandLogoUrlDark?: boolean
    brandTagline?: boolean
    customCss?: boolean
    primaryColor?: boolean
    accentColor?: boolean
    emailButtonColor?: boolean
    loginBgColor?: boolean
    loginCardColor?: boolean
    loginTextColor?: boolean
    loginInputColor?: boolean
    loginRingColor?: boolean
    loginBgColorDark?: boolean
    loginCardColorDark?: boolean
    loginTextColorDark?: boolean
    loginInputColorDark?: boolean
    loginRingColorDark?: boolean
    sidebarBgColor?: boolean
    sidebarTextColor?: boolean
    sidebarAccentColor?: boolean
    faviconUrl?: boolean
    loginHeading?: boolean
    loginSubheading?: boolean
    disabledPlugins?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["appSettings"]>

  export type AppSettingsSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    brandName?: boolean
    brandLogoUrl?: boolean
    brandLogoUrlDark?: boolean
    brandTagline?: boolean
    customCss?: boolean
    primaryColor?: boolean
    accentColor?: boolean
    emailButtonColor?: boolean
    loginBgColor?: boolean
    loginCardColor?: boolean
    loginTextColor?: boolean
    loginInputColor?: boolean
    loginRingColor?: boolean
    loginBgColorDark?: boolean
    loginCardColorDark?: boolean
    loginTextColorDark?: boolean
    loginInputColorDark?: boolean
    loginRingColorDark?: boolean
    sidebarBgColor?: boolean
    sidebarTextColor?: boolean
    sidebarAccentColor?: boolean
    faviconUrl?: boolean
    loginHeading?: boolean
    loginSubheading?: boolean
    disabledPlugins?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["appSettings"]>

  export type AppSettingsSelectScalar = {
    id?: boolean
    brandName?: boolean
    brandLogoUrl?: boolean
    brandLogoUrlDark?: boolean
    brandTagline?: boolean
    customCss?: boolean
    primaryColor?: boolean
    accentColor?: boolean
    emailButtonColor?: boolean
    loginBgColor?: boolean
    loginCardColor?: boolean
    loginTextColor?: boolean
    loginInputColor?: boolean
    loginRingColor?: boolean
    loginBgColorDark?: boolean
    loginCardColorDark?: boolean
    loginTextColorDark?: boolean
    loginInputColorDark?: boolean
    loginRingColorDark?: boolean
    sidebarBgColor?: boolean
    sidebarTextColor?: boolean
    sidebarAccentColor?: boolean
    faviconUrl?: boolean
    loginHeading?: boolean
    loginSubheading?: boolean
    disabledPlugins?: boolean
    updatedAt?: boolean
  }

  export type AppSettingsOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "brandName" | "brandLogoUrl" | "brandLogoUrlDark" | "brandTagline" | "customCss" | "primaryColor" | "accentColor" | "emailButtonColor" | "loginBgColor" | "loginCardColor" | "loginTextColor" | "loginInputColor" | "loginRingColor" | "loginBgColorDark" | "loginCardColorDark" | "loginTextColorDark" | "loginInputColorDark" | "loginRingColorDark" | "sidebarBgColor" | "sidebarTextColor" | "sidebarAccentColor" | "faviconUrl" | "loginHeading" | "loginSubheading" | "disabledPlugins" | "updatedAt", ExtArgs["result"]["appSettings"]>

  export type $AppSettingsPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "AppSettings"
    objects: {}
    scalars: $Extensions.GetPayloadResult<{
      id: string
      brandName: string | null
      brandLogoUrl: string | null
      brandLogoUrlDark: string | null
      brandTagline: string | null
      customCss: string | null
      primaryColor: string | null
      accentColor: string | null
      emailButtonColor: string | null
      loginBgColor: string | null
      loginCardColor: string | null
      loginTextColor: string | null
      loginInputColor: string | null
      loginRingColor: string | null
      loginBgColorDark: string | null
      loginCardColorDark: string | null
      loginTextColorDark: string | null
      loginInputColorDark: string | null
      loginRingColorDark: string | null
      sidebarBgColor: string | null
      sidebarTextColor: string | null
      sidebarAccentColor: string | null
      faviconUrl: string | null
      loginHeading: string | null
      loginSubheading: string | null
      disabledPlugins: string | null
      updatedAt: Date
    }, ExtArgs["result"]["appSettings"]>
    composites: {}
  }

  type AppSettingsGetPayload<S extends boolean | null | undefined | AppSettingsDefaultArgs> = $Result.GetResult<Prisma.$AppSettingsPayload, S>

  type AppSettingsCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<AppSettingsFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: AppSettingsCountAggregateInputType | true
    }

  export interface AppSettingsDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['AppSettings'], meta: { name: 'AppSettings' } }
    /**
     * Find zero or one AppSettings that matches the filter.
     * @param {AppSettingsFindUniqueArgs} args - Arguments to find a AppSettings
     * @example
     * // Get one AppSettings
     * const appSettings = await prisma.appSettings.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends AppSettingsFindUniqueArgs>(args: SelectSubset<T, AppSettingsFindUniqueArgs<ExtArgs>>): Prisma__AppSettingsClient<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one AppSettings that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {AppSettingsFindUniqueOrThrowArgs} args - Arguments to find a AppSettings
     * @example
     * // Get one AppSettings
     * const appSettings = await prisma.appSettings.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends AppSettingsFindUniqueOrThrowArgs>(args: SelectSubset<T, AppSettingsFindUniqueOrThrowArgs<ExtArgs>>): Prisma__AppSettingsClient<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first AppSettings that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AppSettingsFindFirstArgs} args - Arguments to find a AppSettings
     * @example
     * // Get one AppSettings
     * const appSettings = await prisma.appSettings.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends AppSettingsFindFirstArgs>(args?: SelectSubset<T, AppSettingsFindFirstArgs<ExtArgs>>): Prisma__AppSettingsClient<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first AppSettings that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AppSettingsFindFirstOrThrowArgs} args - Arguments to find a AppSettings
     * @example
     * // Get one AppSettings
     * const appSettings = await prisma.appSettings.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends AppSettingsFindFirstOrThrowArgs>(args?: SelectSubset<T, AppSettingsFindFirstOrThrowArgs<ExtArgs>>): Prisma__AppSettingsClient<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more AppSettings that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AppSettingsFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all AppSettings
     * const appSettings = await prisma.appSettings.findMany()
     * 
     * // Get first 10 AppSettings
     * const appSettings = await prisma.appSettings.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const appSettingsWithIdOnly = await prisma.appSettings.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends AppSettingsFindManyArgs>(args?: SelectSubset<T, AppSettingsFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a AppSettings.
     * @param {AppSettingsCreateArgs} args - Arguments to create a AppSettings.
     * @example
     * // Create one AppSettings
     * const AppSettings = await prisma.appSettings.create({
     *   data: {
     *     // ... data to create a AppSettings
     *   }
     * })
     * 
     */
    create<T extends AppSettingsCreateArgs>(args: SelectSubset<T, AppSettingsCreateArgs<ExtArgs>>): Prisma__AppSettingsClient<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many AppSettings.
     * @param {AppSettingsCreateManyArgs} args - Arguments to create many AppSettings.
     * @example
     * // Create many AppSettings
     * const appSettings = await prisma.appSettings.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends AppSettingsCreateManyArgs>(args?: SelectSubset<T, AppSettingsCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many AppSettings and returns the data saved in the database.
     * @param {AppSettingsCreateManyAndReturnArgs} args - Arguments to create many AppSettings.
     * @example
     * // Create many AppSettings
     * const appSettings = await prisma.appSettings.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many AppSettings and only return the `id`
     * const appSettingsWithIdOnly = await prisma.appSettings.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends AppSettingsCreateManyAndReturnArgs>(args?: SelectSubset<T, AppSettingsCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a AppSettings.
     * @param {AppSettingsDeleteArgs} args - Arguments to delete one AppSettings.
     * @example
     * // Delete one AppSettings
     * const AppSettings = await prisma.appSettings.delete({
     *   where: {
     *     // ... filter to delete one AppSettings
     *   }
     * })
     * 
     */
    delete<T extends AppSettingsDeleteArgs>(args: SelectSubset<T, AppSettingsDeleteArgs<ExtArgs>>): Prisma__AppSettingsClient<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one AppSettings.
     * @param {AppSettingsUpdateArgs} args - Arguments to update one AppSettings.
     * @example
     * // Update one AppSettings
     * const appSettings = await prisma.appSettings.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends AppSettingsUpdateArgs>(args: SelectSubset<T, AppSettingsUpdateArgs<ExtArgs>>): Prisma__AppSettingsClient<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more AppSettings.
     * @param {AppSettingsDeleteManyArgs} args - Arguments to filter AppSettings to delete.
     * @example
     * // Delete a few AppSettings
     * const { count } = await prisma.appSettings.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends AppSettingsDeleteManyArgs>(args?: SelectSubset<T, AppSettingsDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more AppSettings.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AppSettingsUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many AppSettings
     * const appSettings = await prisma.appSettings.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends AppSettingsUpdateManyArgs>(args: SelectSubset<T, AppSettingsUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more AppSettings and returns the data updated in the database.
     * @param {AppSettingsUpdateManyAndReturnArgs} args - Arguments to update many AppSettings.
     * @example
     * // Update many AppSettings
     * const appSettings = await prisma.appSettings.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more AppSettings and only return the `id`
     * const appSettingsWithIdOnly = await prisma.appSettings.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends AppSettingsUpdateManyAndReturnArgs>(args: SelectSubset<T, AppSettingsUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one AppSettings.
     * @param {AppSettingsUpsertArgs} args - Arguments to update or create a AppSettings.
     * @example
     * // Update or create a AppSettings
     * const appSettings = await prisma.appSettings.upsert({
     *   create: {
     *     // ... data to create a AppSettings
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the AppSettings we want to update
     *   }
     * })
     */
    upsert<T extends AppSettingsUpsertArgs>(args: SelectSubset<T, AppSettingsUpsertArgs<ExtArgs>>): Prisma__AppSettingsClient<$Result.GetResult<Prisma.$AppSettingsPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of AppSettings.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AppSettingsCountArgs} args - Arguments to filter AppSettings to count.
     * @example
     * // Count the number of AppSettings
     * const count = await prisma.appSettings.count({
     *   where: {
     *     // ... the filter for the AppSettings we want to count
     *   }
     * })
    **/
    count<T extends AppSettingsCountArgs>(
      args?: Subset<T, AppSettingsCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], AppSettingsCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a AppSettings.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AppSettingsAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends AppSettingsAggregateArgs>(args: Subset<T, AppSettingsAggregateArgs>): Prisma.PrismaPromise<GetAppSettingsAggregateType<T>>

    /**
     * Group by AppSettings.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AppSettingsGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends AppSettingsGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: AppSettingsGroupByArgs['orderBy'] }
        : { orderBy?: AppSettingsGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, AppSettingsGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetAppSettingsGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the AppSettings model
   */
  readonly fields: AppSettingsFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for AppSettings.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__AppSettingsClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the AppSettings model
   */
  interface AppSettingsFieldRefs {
    readonly id: FieldRef<"AppSettings", 'String'>
    readonly brandName: FieldRef<"AppSettings", 'String'>
    readonly brandLogoUrl: FieldRef<"AppSettings", 'String'>
    readonly brandLogoUrlDark: FieldRef<"AppSettings", 'String'>
    readonly brandTagline: FieldRef<"AppSettings", 'String'>
    readonly customCss: FieldRef<"AppSettings", 'String'>
    readonly primaryColor: FieldRef<"AppSettings", 'String'>
    readonly accentColor: FieldRef<"AppSettings", 'String'>
    readonly emailButtonColor: FieldRef<"AppSettings", 'String'>
    readonly loginBgColor: FieldRef<"AppSettings", 'String'>
    readonly loginCardColor: FieldRef<"AppSettings", 'String'>
    readonly loginTextColor: FieldRef<"AppSettings", 'String'>
    readonly loginInputColor: FieldRef<"AppSettings", 'String'>
    readonly loginRingColor: FieldRef<"AppSettings", 'String'>
    readonly loginBgColorDark: FieldRef<"AppSettings", 'String'>
    readonly loginCardColorDark: FieldRef<"AppSettings", 'String'>
    readonly loginTextColorDark: FieldRef<"AppSettings", 'String'>
    readonly loginInputColorDark: FieldRef<"AppSettings", 'String'>
    readonly loginRingColorDark: FieldRef<"AppSettings", 'String'>
    readonly sidebarBgColor: FieldRef<"AppSettings", 'String'>
    readonly sidebarTextColor: FieldRef<"AppSettings", 'String'>
    readonly sidebarAccentColor: FieldRef<"AppSettings", 'String'>
    readonly faviconUrl: FieldRef<"AppSettings", 'String'>
    readonly loginHeading: FieldRef<"AppSettings", 'String'>
    readonly loginSubheading: FieldRef<"AppSettings", 'String'>
    readonly disabledPlugins: FieldRef<"AppSettings", 'String'>
    readonly updatedAt: FieldRef<"AppSettings", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * AppSettings findUnique
   */
  export type AppSettingsFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * Filter, which AppSettings to fetch.
     */
    where: AppSettingsWhereUniqueInput
  }

  /**
   * AppSettings findUniqueOrThrow
   */
  export type AppSettingsFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * Filter, which AppSettings to fetch.
     */
    where: AppSettingsWhereUniqueInput
  }

  /**
   * AppSettings findFirst
   */
  export type AppSettingsFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * Filter, which AppSettings to fetch.
     */
    where?: AppSettingsWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AppSettings to fetch.
     */
    orderBy?: AppSettingsOrderByWithRelationInput | AppSettingsOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for AppSettings.
     */
    cursor?: AppSettingsWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AppSettings from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AppSettings.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of AppSettings.
     */
    distinct?: AppSettingsScalarFieldEnum | AppSettingsScalarFieldEnum[]
  }

  /**
   * AppSettings findFirstOrThrow
   */
  export type AppSettingsFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * Filter, which AppSettings to fetch.
     */
    where?: AppSettingsWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AppSettings to fetch.
     */
    orderBy?: AppSettingsOrderByWithRelationInput | AppSettingsOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for AppSettings.
     */
    cursor?: AppSettingsWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AppSettings from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AppSettings.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of AppSettings.
     */
    distinct?: AppSettingsScalarFieldEnum | AppSettingsScalarFieldEnum[]
  }

  /**
   * AppSettings findMany
   */
  export type AppSettingsFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * Filter, which AppSettings to fetch.
     */
    where?: AppSettingsWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AppSettings to fetch.
     */
    orderBy?: AppSettingsOrderByWithRelationInput | AppSettingsOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing AppSettings.
     */
    cursor?: AppSettingsWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AppSettings from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AppSettings.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of AppSettings.
     */
    distinct?: AppSettingsScalarFieldEnum | AppSettingsScalarFieldEnum[]
  }

  /**
   * AppSettings create
   */
  export type AppSettingsCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * The data needed to create a AppSettings.
     */
    data: XOR<AppSettingsCreateInput, AppSettingsUncheckedCreateInput>
  }

  /**
   * AppSettings createMany
   */
  export type AppSettingsCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many AppSettings.
     */
    data: AppSettingsCreateManyInput | AppSettingsCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * AppSettings createManyAndReturn
   */
  export type AppSettingsCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * The data used to create many AppSettings.
     */
    data: AppSettingsCreateManyInput | AppSettingsCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * AppSettings update
   */
  export type AppSettingsUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * The data needed to update a AppSettings.
     */
    data: XOR<AppSettingsUpdateInput, AppSettingsUncheckedUpdateInput>
    /**
     * Choose, which AppSettings to update.
     */
    where: AppSettingsWhereUniqueInput
  }

  /**
   * AppSettings updateMany
   */
  export type AppSettingsUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update AppSettings.
     */
    data: XOR<AppSettingsUpdateManyMutationInput, AppSettingsUncheckedUpdateManyInput>
    /**
     * Filter which AppSettings to update
     */
    where?: AppSettingsWhereInput
    /**
     * Limit how many AppSettings to update.
     */
    limit?: number
  }

  /**
   * AppSettings updateManyAndReturn
   */
  export type AppSettingsUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * The data used to update AppSettings.
     */
    data: XOR<AppSettingsUpdateManyMutationInput, AppSettingsUncheckedUpdateManyInput>
    /**
     * Filter which AppSettings to update
     */
    where?: AppSettingsWhereInput
    /**
     * Limit how many AppSettings to update.
     */
    limit?: number
  }

  /**
   * AppSettings upsert
   */
  export type AppSettingsUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * The filter to search for the AppSettings to update in case it exists.
     */
    where: AppSettingsWhereUniqueInput
    /**
     * In case the AppSettings found by the `where` argument doesn't exist, create a new AppSettings with this data.
     */
    create: XOR<AppSettingsCreateInput, AppSettingsUncheckedCreateInput>
    /**
     * In case the AppSettings was found with the provided `where` argument, update it with this data.
     */
    update: XOR<AppSettingsUpdateInput, AppSettingsUncheckedUpdateInput>
  }

  /**
   * AppSettings delete
   */
  export type AppSettingsDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
    /**
     * Filter which AppSettings to delete.
     */
    where: AppSettingsWhereUniqueInput
  }

  /**
   * AppSettings deleteMany
   */
  export type AppSettingsDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which AppSettings to delete
     */
    where?: AppSettingsWhereInput
    /**
     * Limit how many AppSettings to delete.
     */
    limit?: number
  }

  /**
   * AppSettings without action
   */
  export type AppSettingsDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AppSettings
     */
    select?: AppSettingsSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AppSettings
     */
    omit?: AppSettingsOmit<ExtArgs> | null
  }


  /**
   * Model AuditLog
   */

  export type AggregateAuditLog = {
    _count: AuditLogCountAggregateOutputType | null
    _min: AuditLogMinAggregateOutputType | null
    _max: AuditLogMaxAggregateOutputType | null
  }

  export type AuditLogMinAggregateOutputType = {
    id: string | null
    tenantId: string | null
    userId: string | null
    action: string | null
    entity: string | null
    entityId: string | null
    ipAddress: string | null
    createdAt: Date | null
    impersonatedBy: string | null
  }

  export type AuditLogMaxAggregateOutputType = {
    id: string | null
    tenantId: string | null
    userId: string | null
    action: string | null
    entity: string | null
    entityId: string | null
    ipAddress: string | null
    createdAt: Date | null
    impersonatedBy: string | null
  }

  export type AuditLogCountAggregateOutputType = {
    id: number
    tenantId: number
    userId: number
    action: number
    entity: number
    entityId: number
    metadata: number
    ipAddress: number
    createdAt: number
    impersonatedBy: number
    _all: number
  }


  export type AuditLogMinAggregateInputType = {
    id?: true
    tenantId?: true
    userId?: true
    action?: true
    entity?: true
    entityId?: true
    ipAddress?: true
    createdAt?: true
    impersonatedBy?: true
  }

  export type AuditLogMaxAggregateInputType = {
    id?: true
    tenantId?: true
    userId?: true
    action?: true
    entity?: true
    entityId?: true
    ipAddress?: true
    createdAt?: true
    impersonatedBy?: true
  }

  export type AuditLogCountAggregateInputType = {
    id?: true
    tenantId?: true
    userId?: true
    action?: true
    entity?: true
    entityId?: true
    metadata?: true
    ipAddress?: true
    createdAt?: true
    impersonatedBy?: true
    _all?: true
  }

  export type AuditLogAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which AuditLog to aggregate.
     */
    where?: AuditLogWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AuditLogs to fetch.
     */
    orderBy?: AuditLogOrderByWithRelationInput | AuditLogOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: AuditLogWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AuditLogs from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AuditLogs.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned AuditLogs
    **/
    _count?: true | AuditLogCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: AuditLogMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: AuditLogMaxAggregateInputType
  }

  export type GetAuditLogAggregateType<T extends AuditLogAggregateArgs> = {
        [P in keyof T & keyof AggregateAuditLog]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateAuditLog[P]>
      : GetScalarType<T[P], AggregateAuditLog[P]>
  }




  export type AuditLogGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: AuditLogWhereInput
    orderBy?: AuditLogOrderByWithAggregationInput | AuditLogOrderByWithAggregationInput[]
    by: AuditLogScalarFieldEnum[] | AuditLogScalarFieldEnum
    having?: AuditLogScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: AuditLogCountAggregateInputType | true
    _min?: AuditLogMinAggregateInputType
    _max?: AuditLogMaxAggregateInputType
  }

  export type AuditLogGroupByOutputType = {
    id: string
    tenantId: string | null
    userId: string | null
    action: string
    entity: string
    entityId: string | null
    metadata: JsonValue
    ipAddress: string | null
    createdAt: Date
    impersonatedBy: string | null
    _count: AuditLogCountAggregateOutputType | null
    _min: AuditLogMinAggregateOutputType | null
    _max: AuditLogMaxAggregateOutputType | null
  }

  type GetAuditLogGroupByPayload<T extends AuditLogGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<AuditLogGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof AuditLogGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], AuditLogGroupByOutputType[P]>
            : GetScalarType<T[P], AuditLogGroupByOutputType[P]>
        }
      >
    >


  export type AuditLogSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    tenantId?: boolean
    userId?: boolean
    action?: boolean
    entity?: boolean
    entityId?: boolean
    metadata?: boolean
    ipAddress?: boolean
    createdAt?: boolean
    impersonatedBy?: boolean
  }, ExtArgs["result"]["auditLog"]>

  export type AuditLogSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    tenantId?: boolean
    userId?: boolean
    action?: boolean
    entity?: boolean
    entityId?: boolean
    metadata?: boolean
    ipAddress?: boolean
    createdAt?: boolean
    impersonatedBy?: boolean
  }, ExtArgs["result"]["auditLog"]>

  export type AuditLogSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    tenantId?: boolean
    userId?: boolean
    action?: boolean
    entity?: boolean
    entityId?: boolean
    metadata?: boolean
    ipAddress?: boolean
    createdAt?: boolean
    impersonatedBy?: boolean
  }, ExtArgs["result"]["auditLog"]>

  export type AuditLogSelectScalar = {
    id?: boolean
    tenantId?: boolean
    userId?: boolean
    action?: boolean
    entity?: boolean
    entityId?: boolean
    metadata?: boolean
    ipAddress?: boolean
    createdAt?: boolean
    impersonatedBy?: boolean
  }

  export type AuditLogOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "tenantId" | "userId" | "action" | "entity" | "entityId" | "metadata" | "ipAddress" | "createdAt" | "impersonatedBy", ExtArgs["result"]["auditLog"]>

  export type $AuditLogPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "AuditLog"
    objects: {}
    scalars: $Extensions.GetPayloadResult<{
      id: string
      tenantId: string | null
      userId: string | null
      action: string
      entity: string
      entityId: string | null
      metadata: Prisma.JsonValue
      ipAddress: string | null
      createdAt: Date
      /**
       * Set when this action was performed by a super admin assisting the tenant.
       */
      impersonatedBy: string | null
    }, ExtArgs["result"]["auditLog"]>
    composites: {}
  }

  type AuditLogGetPayload<S extends boolean | null | undefined | AuditLogDefaultArgs> = $Result.GetResult<Prisma.$AuditLogPayload, S>

  type AuditLogCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<AuditLogFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: AuditLogCountAggregateInputType | true
    }

  export interface AuditLogDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['AuditLog'], meta: { name: 'AuditLog' } }
    /**
     * Find zero or one AuditLog that matches the filter.
     * @param {AuditLogFindUniqueArgs} args - Arguments to find a AuditLog
     * @example
     * // Get one AuditLog
     * const auditLog = await prisma.auditLog.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends AuditLogFindUniqueArgs>(args: SelectSubset<T, AuditLogFindUniqueArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one AuditLog that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {AuditLogFindUniqueOrThrowArgs} args - Arguments to find a AuditLog
     * @example
     * // Get one AuditLog
     * const auditLog = await prisma.auditLog.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends AuditLogFindUniqueOrThrowArgs>(args: SelectSubset<T, AuditLogFindUniqueOrThrowArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first AuditLog that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogFindFirstArgs} args - Arguments to find a AuditLog
     * @example
     * // Get one AuditLog
     * const auditLog = await prisma.auditLog.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends AuditLogFindFirstArgs>(args?: SelectSubset<T, AuditLogFindFirstArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first AuditLog that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogFindFirstOrThrowArgs} args - Arguments to find a AuditLog
     * @example
     * // Get one AuditLog
     * const auditLog = await prisma.auditLog.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends AuditLogFindFirstOrThrowArgs>(args?: SelectSubset<T, AuditLogFindFirstOrThrowArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more AuditLogs that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all AuditLogs
     * const auditLogs = await prisma.auditLog.findMany()
     * 
     * // Get first 10 AuditLogs
     * const auditLogs = await prisma.auditLog.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const auditLogWithIdOnly = await prisma.auditLog.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends AuditLogFindManyArgs>(args?: SelectSubset<T, AuditLogFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a AuditLog.
     * @param {AuditLogCreateArgs} args - Arguments to create a AuditLog.
     * @example
     * // Create one AuditLog
     * const AuditLog = await prisma.auditLog.create({
     *   data: {
     *     // ... data to create a AuditLog
     *   }
     * })
     * 
     */
    create<T extends AuditLogCreateArgs>(args: SelectSubset<T, AuditLogCreateArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many AuditLogs.
     * @param {AuditLogCreateManyArgs} args - Arguments to create many AuditLogs.
     * @example
     * // Create many AuditLogs
     * const auditLog = await prisma.auditLog.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends AuditLogCreateManyArgs>(args?: SelectSubset<T, AuditLogCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many AuditLogs and returns the data saved in the database.
     * @param {AuditLogCreateManyAndReturnArgs} args - Arguments to create many AuditLogs.
     * @example
     * // Create many AuditLogs
     * const auditLog = await prisma.auditLog.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many AuditLogs and only return the `id`
     * const auditLogWithIdOnly = await prisma.auditLog.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends AuditLogCreateManyAndReturnArgs>(args?: SelectSubset<T, AuditLogCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a AuditLog.
     * @param {AuditLogDeleteArgs} args - Arguments to delete one AuditLog.
     * @example
     * // Delete one AuditLog
     * const AuditLog = await prisma.auditLog.delete({
     *   where: {
     *     // ... filter to delete one AuditLog
     *   }
     * })
     * 
     */
    delete<T extends AuditLogDeleteArgs>(args: SelectSubset<T, AuditLogDeleteArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one AuditLog.
     * @param {AuditLogUpdateArgs} args - Arguments to update one AuditLog.
     * @example
     * // Update one AuditLog
     * const auditLog = await prisma.auditLog.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends AuditLogUpdateArgs>(args: SelectSubset<T, AuditLogUpdateArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more AuditLogs.
     * @param {AuditLogDeleteManyArgs} args - Arguments to filter AuditLogs to delete.
     * @example
     * // Delete a few AuditLogs
     * const { count } = await prisma.auditLog.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends AuditLogDeleteManyArgs>(args?: SelectSubset<T, AuditLogDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more AuditLogs.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many AuditLogs
     * const auditLog = await prisma.auditLog.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends AuditLogUpdateManyArgs>(args: SelectSubset<T, AuditLogUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more AuditLogs and returns the data updated in the database.
     * @param {AuditLogUpdateManyAndReturnArgs} args - Arguments to update many AuditLogs.
     * @example
     * // Update many AuditLogs
     * const auditLog = await prisma.auditLog.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more AuditLogs and only return the `id`
     * const auditLogWithIdOnly = await prisma.auditLog.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends AuditLogUpdateManyAndReturnArgs>(args: SelectSubset<T, AuditLogUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one AuditLog.
     * @param {AuditLogUpsertArgs} args - Arguments to update or create a AuditLog.
     * @example
     * // Update or create a AuditLog
     * const auditLog = await prisma.auditLog.upsert({
     *   create: {
     *     // ... data to create a AuditLog
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the AuditLog we want to update
     *   }
     * })
     */
    upsert<T extends AuditLogUpsertArgs>(args: SelectSubset<T, AuditLogUpsertArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of AuditLogs.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogCountArgs} args - Arguments to filter AuditLogs to count.
     * @example
     * // Count the number of AuditLogs
     * const count = await prisma.auditLog.count({
     *   where: {
     *     // ... the filter for the AuditLogs we want to count
     *   }
     * })
    **/
    count<T extends AuditLogCountArgs>(
      args?: Subset<T, AuditLogCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], AuditLogCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a AuditLog.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends AuditLogAggregateArgs>(args: Subset<T, AuditLogAggregateArgs>): Prisma.PrismaPromise<GetAuditLogAggregateType<T>>

    /**
     * Group by AuditLog.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends AuditLogGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: AuditLogGroupByArgs['orderBy'] }
        : { orderBy?: AuditLogGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, AuditLogGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetAuditLogGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the AuditLog model
   */
  readonly fields: AuditLogFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for AuditLog.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__AuditLogClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the AuditLog model
   */
  interface AuditLogFieldRefs {
    readonly id: FieldRef<"AuditLog", 'String'>
    readonly tenantId: FieldRef<"AuditLog", 'String'>
    readonly userId: FieldRef<"AuditLog", 'String'>
    readonly action: FieldRef<"AuditLog", 'String'>
    readonly entity: FieldRef<"AuditLog", 'String'>
    readonly entityId: FieldRef<"AuditLog", 'String'>
    readonly metadata: FieldRef<"AuditLog", 'Json'>
    readonly ipAddress: FieldRef<"AuditLog", 'String'>
    readonly createdAt: FieldRef<"AuditLog", 'DateTime'>
    readonly impersonatedBy: FieldRef<"AuditLog", 'String'>
  }
    

  // Custom InputTypes
  /**
   * AuditLog findUnique
   */
  export type AuditLogFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter, which AuditLog to fetch.
     */
    where: AuditLogWhereUniqueInput
  }

  /**
   * AuditLog findUniqueOrThrow
   */
  export type AuditLogFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter, which AuditLog to fetch.
     */
    where: AuditLogWhereUniqueInput
  }

  /**
   * AuditLog findFirst
   */
  export type AuditLogFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter, which AuditLog to fetch.
     */
    where?: AuditLogWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AuditLogs to fetch.
     */
    orderBy?: AuditLogOrderByWithRelationInput | AuditLogOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for AuditLogs.
     */
    cursor?: AuditLogWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AuditLogs from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AuditLogs.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of AuditLogs.
     */
    distinct?: AuditLogScalarFieldEnum | AuditLogScalarFieldEnum[]
  }

  /**
   * AuditLog findFirstOrThrow
   */
  export type AuditLogFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter, which AuditLog to fetch.
     */
    where?: AuditLogWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AuditLogs to fetch.
     */
    orderBy?: AuditLogOrderByWithRelationInput | AuditLogOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for AuditLogs.
     */
    cursor?: AuditLogWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AuditLogs from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AuditLogs.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of AuditLogs.
     */
    distinct?: AuditLogScalarFieldEnum | AuditLogScalarFieldEnum[]
  }

  /**
   * AuditLog findMany
   */
  export type AuditLogFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter, which AuditLogs to fetch.
     */
    where?: AuditLogWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AuditLogs to fetch.
     */
    orderBy?: AuditLogOrderByWithRelationInput | AuditLogOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing AuditLogs.
     */
    cursor?: AuditLogWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AuditLogs from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AuditLogs.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of AuditLogs.
     */
    distinct?: AuditLogScalarFieldEnum | AuditLogScalarFieldEnum[]
  }

  /**
   * AuditLog create
   */
  export type AuditLogCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * The data needed to create a AuditLog.
     */
    data: XOR<AuditLogCreateInput, AuditLogUncheckedCreateInput>
  }

  /**
   * AuditLog createMany
   */
  export type AuditLogCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many AuditLogs.
     */
    data: AuditLogCreateManyInput | AuditLogCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * AuditLog createManyAndReturn
   */
  export type AuditLogCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * The data used to create many AuditLogs.
     */
    data: AuditLogCreateManyInput | AuditLogCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * AuditLog update
   */
  export type AuditLogUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * The data needed to update a AuditLog.
     */
    data: XOR<AuditLogUpdateInput, AuditLogUncheckedUpdateInput>
    /**
     * Choose, which AuditLog to update.
     */
    where: AuditLogWhereUniqueInput
  }

  /**
   * AuditLog updateMany
   */
  export type AuditLogUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update AuditLogs.
     */
    data: XOR<AuditLogUpdateManyMutationInput, AuditLogUncheckedUpdateManyInput>
    /**
     * Filter which AuditLogs to update
     */
    where?: AuditLogWhereInput
    /**
     * Limit how many AuditLogs to update.
     */
    limit?: number
  }

  /**
   * AuditLog updateManyAndReturn
   */
  export type AuditLogUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * The data used to update AuditLogs.
     */
    data: XOR<AuditLogUpdateManyMutationInput, AuditLogUncheckedUpdateManyInput>
    /**
     * Filter which AuditLogs to update
     */
    where?: AuditLogWhereInput
    /**
     * Limit how many AuditLogs to update.
     */
    limit?: number
  }

  /**
   * AuditLog upsert
   */
  export type AuditLogUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * The filter to search for the AuditLog to update in case it exists.
     */
    where: AuditLogWhereUniqueInput
    /**
     * In case the AuditLog found by the `where` argument doesn't exist, create a new AuditLog with this data.
     */
    create: XOR<AuditLogCreateInput, AuditLogUncheckedCreateInput>
    /**
     * In case the AuditLog was found with the provided `where` argument, update it with this data.
     */
    update: XOR<AuditLogUpdateInput, AuditLogUncheckedUpdateInput>
  }

  /**
   * AuditLog delete
   */
  export type AuditLogDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter which AuditLog to delete.
     */
    where: AuditLogWhereUniqueInput
  }

  /**
   * AuditLog deleteMany
   */
  export type AuditLogDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which AuditLogs to delete
     */
    where?: AuditLogWhereInput
    /**
     * Limit how many AuditLogs to delete.
     */
    limit?: number
  }

  /**
   * AuditLog without action
   */
  export type AuditLogDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
  }


  /**
   * Model WaitlistEntry
   */

  export type AggregateWaitlistEntry = {
    _count: WaitlistEntryCountAggregateOutputType | null
    _min: WaitlistEntryMinAggregateOutputType | null
    _max: WaitlistEntryMaxAggregateOutputType | null
  }

  export type WaitlistEntryMinAggregateOutputType = {
    id: string | null
    email: string | null
    name: string | null
    company: string | null
    useCase: string | null
    status: $Enums.WaitlistStatus | null
    promotedAt: Date | null
    createdAt: Date | null
  }

  export type WaitlistEntryMaxAggregateOutputType = {
    id: string | null
    email: string | null
    name: string | null
    company: string | null
    useCase: string | null
    status: $Enums.WaitlistStatus | null
    promotedAt: Date | null
    createdAt: Date | null
  }

  export type WaitlistEntryCountAggregateOutputType = {
    id: number
    email: number
    name: number
    company: number
    useCase: number
    status: number
    promotedAt: number
    createdAt: number
    _all: number
  }


  export type WaitlistEntryMinAggregateInputType = {
    id?: true
    email?: true
    name?: true
    company?: true
    useCase?: true
    status?: true
    promotedAt?: true
    createdAt?: true
  }

  export type WaitlistEntryMaxAggregateInputType = {
    id?: true
    email?: true
    name?: true
    company?: true
    useCase?: true
    status?: true
    promotedAt?: true
    createdAt?: true
  }

  export type WaitlistEntryCountAggregateInputType = {
    id?: true
    email?: true
    name?: true
    company?: true
    useCase?: true
    status?: true
    promotedAt?: true
    createdAt?: true
    _all?: true
  }

  export type WaitlistEntryAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which WaitlistEntry to aggregate.
     */
    where?: WaitlistEntryWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of WaitlistEntries to fetch.
     */
    orderBy?: WaitlistEntryOrderByWithRelationInput | WaitlistEntryOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: WaitlistEntryWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` WaitlistEntries from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` WaitlistEntries.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned WaitlistEntries
    **/
    _count?: true | WaitlistEntryCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: WaitlistEntryMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: WaitlistEntryMaxAggregateInputType
  }

  export type GetWaitlistEntryAggregateType<T extends WaitlistEntryAggregateArgs> = {
        [P in keyof T & keyof AggregateWaitlistEntry]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateWaitlistEntry[P]>
      : GetScalarType<T[P], AggregateWaitlistEntry[P]>
  }




  export type WaitlistEntryGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: WaitlistEntryWhereInput
    orderBy?: WaitlistEntryOrderByWithAggregationInput | WaitlistEntryOrderByWithAggregationInput[]
    by: WaitlistEntryScalarFieldEnum[] | WaitlistEntryScalarFieldEnum
    having?: WaitlistEntryScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: WaitlistEntryCountAggregateInputType | true
    _min?: WaitlistEntryMinAggregateInputType
    _max?: WaitlistEntryMaxAggregateInputType
  }

  export type WaitlistEntryGroupByOutputType = {
    id: string
    email: string
    name: string | null
    company: string | null
    useCase: string | null
    status: $Enums.WaitlistStatus
    promotedAt: Date | null
    createdAt: Date
    _count: WaitlistEntryCountAggregateOutputType | null
    _min: WaitlistEntryMinAggregateOutputType | null
    _max: WaitlistEntryMaxAggregateOutputType | null
  }

  type GetWaitlistEntryGroupByPayload<T extends WaitlistEntryGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<WaitlistEntryGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof WaitlistEntryGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], WaitlistEntryGroupByOutputType[P]>
            : GetScalarType<T[P], WaitlistEntryGroupByOutputType[P]>
        }
      >
    >


  export type WaitlistEntrySelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    email?: boolean
    name?: boolean
    company?: boolean
    useCase?: boolean
    status?: boolean
    promotedAt?: boolean
    createdAt?: boolean
  }, ExtArgs["result"]["waitlistEntry"]>

  export type WaitlistEntrySelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    email?: boolean
    name?: boolean
    company?: boolean
    useCase?: boolean
    status?: boolean
    promotedAt?: boolean
    createdAt?: boolean
  }, ExtArgs["result"]["waitlistEntry"]>

  export type WaitlistEntrySelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    email?: boolean
    name?: boolean
    company?: boolean
    useCase?: boolean
    status?: boolean
    promotedAt?: boolean
    createdAt?: boolean
  }, ExtArgs["result"]["waitlistEntry"]>

  export type WaitlistEntrySelectScalar = {
    id?: boolean
    email?: boolean
    name?: boolean
    company?: boolean
    useCase?: boolean
    status?: boolean
    promotedAt?: boolean
    createdAt?: boolean
  }

  export type WaitlistEntryOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "email" | "name" | "company" | "useCase" | "status" | "promotedAt" | "createdAt", ExtArgs["result"]["waitlistEntry"]>

  export type $WaitlistEntryPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "WaitlistEntry"
    objects: {}
    scalars: $Extensions.GetPayloadResult<{
      id: string
      email: string
      name: string | null
      company: string | null
      useCase: string | null
      status: $Enums.WaitlistStatus
      promotedAt: Date | null
      createdAt: Date
    }, ExtArgs["result"]["waitlistEntry"]>
    composites: {}
  }

  type WaitlistEntryGetPayload<S extends boolean | null | undefined | WaitlistEntryDefaultArgs> = $Result.GetResult<Prisma.$WaitlistEntryPayload, S>

  type WaitlistEntryCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<WaitlistEntryFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: WaitlistEntryCountAggregateInputType | true
    }

  export interface WaitlistEntryDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['WaitlistEntry'], meta: { name: 'WaitlistEntry' } }
    /**
     * Find zero or one WaitlistEntry that matches the filter.
     * @param {WaitlistEntryFindUniqueArgs} args - Arguments to find a WaitlistEntry
     * @example
     * // Get one WaitlistEntry
     * const waitlistEntry = await prisma.waitlistEntry.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends WaitlistEntryFindUniqueArgs>(args: SelectSubset<T, WaitlistEntryFindUniqueArgs<ExtArgs>>): Prisma__WaitlistEntryClient<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one WaitlistEntry that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {WaitlistEntryFindUniqueOrThrowArgs} args - Arguments to find a WaitlistEntry
     * @example
     * // Get one WaitlistEntry
     * const waitlistEntry = await prisma.waitlistEntry.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends WaitlistEntryFindUniqueOrThrowArgs>(args: SelectSubset<T, WaitlistEntryFindUniqueOrThrowArgs<ExtArgs>>): Prisma__WaitlistEntryClient<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first WaitlistEntry that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WaitlistEntryFindFirstArgs} args - Arguments to find a WaitlistEntry
     * @example
     * // Get one WaitlistEntry
     * const waitlistEntry = await prisma.waitlistEntry.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends WaitlistEntryFindFirstArgs>(args?: SelectSubset<T, WaitlistEntryFindFirstArgs<ExtArgs>>): Prisma__WaitlistEntryClient<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first WaitlistEntry that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WaitlistEntryFindFirstOrThrowArgs} args - Arguments to find a WaitlistEntry
     * @example
     * // Get one WaitlistEntry
     * const waitlistEntry = await prisma.waitlistEntry.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends WaitlistEntryFindFirstOrThrowArgs>(args?: SelectSubset<T, WaitlistEntryFindFirstOrThrowArgs<ExtArgs>>): Prisma__WaitlistEntryClient<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more WaitlistEntries that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WaitlistEntryFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all WaitlistEntries
     * const waitlistEntries = await prisma.waitlistEntry.findMany()
     * 
     * // Get first 10 WaitlistEntries
     * const waitlistEntries = await prisma.waitlistEntry.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const waitlistEntryWithIdOnly = await prisma.waitlistEntry.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends WaitlistEntryFindManyArgs>(args?: SelectSubset<T, WaitlistEntryFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a WaitlistEntry.
     * @param {WaitlistEntryCreateArgs} args - Arguments to create a WaitlistEntry.
     * @example
     * // Create one WaitlistEntry
     * const WaitlistEntry = await prisma.waitlistEntry.create({
     *   data: {
     *     // ... data to create a WaitlistEntry
     *   }
     * })
     * 
     */
    create<T extends WaitlistEntryCreateArgs>(args: SelectSubset<T, WaitlistEntryCreateArgs<ExtArgs>>): Prisma__WaitlistEntryClient<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many WaitlistEntries.
     * @param {WaitlistEntryCreateManyArgs} args - Arguments to create many WaitlistEntries.
     * @example
     * // Create many WaitlistEntries
     * const waitlistEntry = await prisma.waitlistEntry.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends WaitlistEntryCreateManyArgs>(args?: SelectSubset<T, WaitlistEntryCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many WaitlistEntries and returns the data saved in the database.
     * @param {WaitlistEntryCreateManyAndReturnArgs} args - Arguments to create many WaitlistEntries.
     * @example
     * // Create many WaitlistEntries
     * const waitlistEntry = await prisma.waitlistEntry.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many WaitlistEntries and only return the `id`
     * const waitlistEntryWithIdOnly = await prisma.waitlistEntry.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends WaitlistEntryCreateManyAndReturnArgs>(args?: SelectSubset<T, WaitlistEntryCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a WaitlistEntry.
     * @param {WaitlistEntryDeleteArgs} args - Arguments to delete one WaitlistEntry.
     * @example
     * // Delete one WaitlistEntry
     * const WaitlistEntry = await prisma.waitlistEntry.delete({
     *   where: {
     *     // ... filter to delete one WaitlistEntry
     *   }
     * })
     * 
     */
    delete<T extends WaitlistEntryDeleteArgs>(args: SelectSubset<T, WaitlistEntryDeleteArgs<ExtArgs>>): Prisma__WaitlistEntryClient<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one WaitlistEntry.
     * @param {WaitlistEntryUpdateArgs} args - Arguments to update one WaitlistEntry.
     * @example
     * // Update one WaitlistEntry
     * const waitlistEntry = await prisma.waitlistEntry.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends WaitlistEntryUpdateArgs>(args: SelectSubset<T, WaitlistEntryUpdateArgs<ExtArgs>>): Prisma__WaitlistEntryClient<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more WaitlistEntries.
     * @param {WaitlistEntryDeleteManyArgs} args - Arguments to filter WaitlistEntries to delete.
     * @example
     * // Delete a few WaitlistEntries
     * const { count } = await prisma.waitlistEntry.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends WaitlistEntryDeleteManyArgs>(args?: SelectSubset<T, WaitlistEntryDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more WaitlistEntries.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WaitlistEntryUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many WaitlistEntries
     * const waitlistEntry = await prisma.waitlistEntry.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends WaitlistEntryUpdateManyArgs>(args: SelectSubset<T, WaitlistEntryUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more WaitlistEntries and returns the data updated in the database.
     * @param {WaitlistEntryUpdateManyAndReturnArgs} args - Arguments to update many WaitlistEntries.
     * @example
     * // Update many WaitlistEntries
     * const waitlistEntry = await prisma.waitlistEntry.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more WaitlistEntries and only return the `id`
     * const waitlistEntryWithIdOnly = await prisma.waitlistEntry.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends WaitlistEntryUpdateManyAndReturnArgs>(args: SelectSubset<T, WaitlistEntryUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one WaitlistEntry.
     * @param {WaitlistEntryUpsertArgs} args - Arguments to update or create a WaitlistEntry.
     * @example
     * // Update or create a WaitlistEntry
     * const waitlistEntry = await prisma.waitlistEntry.upsert({
     *   create: {
     *     // ... data to create a WaitlistEntry
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the WaitlistEntry we want to update
     *   }
     * })
     */
    upsert<T extends WaitlistEntryUpsertArgs>(args: SelectSubset<T, WaitlistEntryUpsertArgs<ExtArgs>>): Prisma__WaitlistEntryClient<$Result.GetResult<Prisma.$WaitlistEntryPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of WaitlistEntries.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WaitlistEntryCountArgs} args - Arguments to filter WaitlistEntries to count.
     * @example
     * // Count the number of WaitlistEntries
     * const count = await prisma.waitlistEntry.count({
     *   where: {
     *     // ... the filter for the WaitlistEntries we want to count
     *   }
     * })
    **/
    count<T extends WaitlistEntryCountArgs>(
      args?: Subset<T, WaitlistEntryCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], WaitlistEntryCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a WaitlistEntry.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WaitlistEntryAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends WaitlistEntryAggregateArgs>(args: Subset<T, WaitlistEntryAggregateArgs>): Prisma.PrismaPromise<GetWaitlistEntryAggregateType<T>>

    /**
     * Group by WaitlistEntry.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WaitlistEntryGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends WaitlistEntryGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: WaitlistEntryGroupByArgs['orderBy'] }
        : { orderBy?: WaitlistEntryGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, WaitlistEntryGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetWaitlistEntryGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the WaitlistEntry model
   */
  readonly fields: WaitlistEntryFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for WaitlistEntry.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__WaitlistEntryClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the WaitlistEntry model
   */
  interface WaitlistEntryFieldRefs {
    readonly id: FieldRef<"WaitlistEntry", 'String'>
    readonly email: FieldRef<"WaitlistEntry", 'String'>
    readonly name: FieldRef<"WaitlistEntry", 'String'>
    readonly company: FieldRef<"WaitlistEntry", 'String'>
    readonly useCase: FieldRef<"WaitlistEntry", 'String'>
    readonly status: FieldRef<"WaitlistEntry", 'WaitlistStatus'>
    readonly promotedAt: FieldRef<"WaitlistEntry", 'DateTime'>
    readonly createdAt: FieldRef<"WaitlistEntry", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * WaitlistEntry findUnique
   */
  export type WaitlistEntryFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelect<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * Filter, which WaitlistEntry to fetch.
     */
    where: WaitlistEntryWhereUniqueInput
  }

  /**
   * WaitlistEntry findUniqueOrThrow
   */
  export type WaitlistEntryFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelect<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * Filter, which WaitlistEntry to fetch.
     */
    where: WaitlistEntryWhereUniqueInput
  }

  /**
   * WaitlistEntry findFirst
   */
  export type WaitlistEntryFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelect<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * Filter, which WaitlistEntry to fetch.
     */
    where?: WaitlistEntryWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of WaitlistEntries to fetch.
     */
    orderBy?: WaitlistEntryOrderByWithRelationInput | WaitlistEntryOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for WaitlistEntries.
     */
    cursor?: WaitlistEntryWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` WaitlistEntries from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` WaitlistEntries.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of WaitlistEntries.
     */
    distinct?: WaitlistEntryScalarFieldEnum | WaitlistEntryScalarFieldEnum[]
  }

  /**
   * WaitlistEntry findFirstOrThrow
   */
  export type WaitlistEntryFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelect<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * Filter, which WaitlistEntry to fetch.
     */
    where?: WaitlistEntryWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of WaitlistEntries to fetch.
     */
    orderBy?: WaitlistEntryOrderByWithRelationInput | WaitlistEntryOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for WaitlistEntries.
     */
    cursor?: WaitlistEntryWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` WaitlistEntries from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` WaitlistEntries.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of WaitlistEntries.
     */
    distinct?: WaitlistEntryScalarFieldEnum | WaitlistEntryScalarFieldEnum[]
  }

  /**
   * WaitlistEntry findMany
   */
  export type WaitlistEntryFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelect<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * Filter, which WaitlistEntries to fetch.
     */
    where?: WaitlistEntryWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of WaitlistEntries to fetch.
     */
    orderBy?: WaitlistEntryOrderByWithRelationInput | WaitlistEntryOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing WaitlistEntries.
     */
    cursor?: WaitlistEntryWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` WaitlistEntries from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` WaitlistEntries.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of WaitlistEntries.
     */
    distinct?: WaitlistEntryScalarFieldEnum | WaitlistEntryScalarFieldEnum[]
  }

  /**
   * WaitlistEntry create
   */
  export type WaitlistEntryCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelect<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * The data needed to create a WaitlistEntry.
     */
    data: XOR<WaitlistEntryCreateInput, WaitlistEntryUncheckedCreateInput>
  }

  /**
   * WaitlistEntry createMany
   */
  export type WaitlistEntryCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many WaitlistEntries.
     */
    data: WaitlistEntryCreateManyInput | WaitlistEntryCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * WaitlistEntry createManyAndReturn
   */
  export type WaitlistEntryCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * The data used to create many WaitlistEntries.
     */
    data: WaitlistEntryCreateManyInput | WaitlistEntryCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * WaitlistEntry update
   */
  export type WaitlistEntryUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelect<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * The data needed to update a WaitlistEntry.
     */
    data: XOR<WaitlistEntryUpdateInput, WaitlistEntryUncheckedUpdateInput>
    /**
     * Choose, which WaitlistEntry to update.
     */
    where: WaitlistEntryWhereUniqueInput
  }

  /**
   * WaitlistEntry updateMany
   */
  export type WaitlistEntryUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update WaitlistEntries.
     */
    data: XOR<WaitlistEntryUpdateManyMutationInput, WaitlistEntryUncheckedUpdateManyInput>
    /**
     * Filter which WaitlistEntries to update
     */
    where?: WaitlistEntryWhereInput
    /**
     * Limit how many WaitlistEntries to update.
     */
    limit?: number
  }

  /**
   * WaitlistEntry updateManyAndReturn
   */
  export type WaitlistEntryUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * The data used to update WaitlistEntries.
     */
    data: XOR<WaitlistEntryUpdateManyMutationInput, WaitlistEntryUncheckedUpdateManyInput>
    /**
     * Filter which WaitlistEntries to update
     */
    where?: WaitlistEntryWhereInput
    /**
     * Limit how many WaitlistEntries to update.
     */
    limit?: number
  }

  /**
   * WaitlistEntry upsert
   */
  export type WaitlistEntryUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelect<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * The filter to search for the WaitlistEntry to update in case it exists.
     */
    where: WaitlistEntryWhereUniqueInput
    /**
     * In case the WaitlistEntry found by the `where` argument doesn't exist, create a new WaitlistEntry with this data.
     */
    create: XOR<WaitlistEntryCreateInput, WaitlistEntryUncheckedCreateInput>
    /**
     * In case the WaitlistEntry was found with the provided `where` argument, update it with this data.
     */
    update: XOR<WaitlistEntryUpdateInput, WaitlistEntryUncheckedUpdateInput>
  }

  /**
   * WaitlistEntry delete
   */
  export type WaitlistEntryDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelect<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
    /**
     * Filter which WaitlistEntry to delete.
     */
    where: WaitlistEntryWhereUniqueInput
  }

  /**
   * WaitlistEntry deleteMany
   */
  export type WaitlistEntryDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which WaitlistEntries to delete
     */
    where?: WaitlistEntryWhereInput
    /**
     * Limit how many WaitlistEntries to delete.
     */
    limit?: number
  }

  /**
   * WaitlistEntry without action
   */
  export type WaitlistEntryDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the WaitlistEntry
     */
    select?: WaitlistEntrySelect<ExtArgs> | null
    /**
     * Omit specific fields from the WaitlistEntry
     */
    omit?: WaitlistEntryOmit<ExtArgs> | null
  }


  /**
   * Model Annotation
   */

  export type AggregateAnnotation = {
    _count: AnnotationCountAggregateOutputType | null
    _avg: AnnotationAvgAggregateOutputType | null
    _sum: AnnotationSumAggregateOutputType | null
    _min: AnnotationMinAggregateOutputType | null
    _max: AnnotationMaxAggregateOutputType | null
  }

  export type AnnotationAvgAggregateOutputType = {
    pageNum: number | null
  }

  export type AnnotationSumAggregateOutputType = {
    pageNum: number | null
  }

  export type AnnotationMinAggregateOutputType = {
    id: string | null
    jobId: string | null
    tenantId: string | null
    pageNum: number | null
    authorId: string | null
    authorEmail: string | null
    authorName: string | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type AnnotationMaxAggregateOutputType = {
    id: string | null
    jobId: string | null
    tenantId: string | null
    pageNum: number | null
    authorId: string | null
    authorEmail: string | null
    authorName: string | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type AnnotationCountAggregateOutputType = {
    id: number
    jobId: number
    tenantId: number
    pageNum: number
    authorId: number
    authorEmail: number
    authorName: number
    fabricJson: number
    createdAt: number
    updatedAt: number
    _all: number
  }


  export type AnnotationAvgAggregateInputType = {
    pageNum?: true
  }

  export type AnnotationSumAggregateInputType = {
    pageNum?: true
  }

  export type AnnotationMinAggregateInputType = {
    id?: true
    jobId?: true
    tenantId?: true
    pageNum?: true
    authorId?: true
    authorEmail?: true
    authorName?: true
    createdAt?: true
    updatedAt?: true
  }

  export type AnnotationMaxAggregateInputType = {
    id?: true
    jobId?: true
    tenantId?: true
    pageNum?: true
    authorId?: true
    authorEmail?: true
    authorName?: true
    createdAt?: true
    updatedAt?: true
  }

  export type AnnotationCountAggregateInputType = {
    id?: true
    jobId?: true
    tenantId?: true
    pageNum?: true
    authorId?: true
    authorEmail?: true
    authorName?: true
    fabricJson?: true
    createdAt?: true
    updatedAt?: true
    _all?: true
  }

  export type AnnotationAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Annotation to aggregate.
     */
    where?: AnnotationWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Annotations to fetch.
     */
    orderBy?: AnnotationOrderByWithRelationInput | AnnotationOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: AnnotationWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Annotations from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Annotations.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Annotations
    **/
    _count?: true | AnnotationCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to average
    **/
    _avg?: AnnotationAvgAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to sum
    **/
    _sum?: AnnotationSumAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: AnnotationMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: AnnotationMaxAggregateInputType
  }

  export type GetAnnotationAggregateType<T extends AnnotationAggregateArgs> = {
        [P in keyof T & keyof AggregateAnnotation]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateAnnotation[P]>
      : GetScalarType<T[P], AggregateAnnotation[P]>
  }




  export type AnnotationGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: AnnotationWhereInput
    orderBy?: AnnotationOrderByWithAggregationInput | AnnotationOrderByWithAggregationInput[]
    by: AnnotationScalarFieldEnum[] | AnnotationScalarFieldEnum
    having?: AnnotationScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: AnnotationCountAggregateInputType | true
    _avg?: AnnotationAvgAggregateInputType
    _sum?: AnnotationSumAggregateInputType
    _min?: AnnotationMinAggregateInputType
    _max?: AnnotationMaxAggregateInputType
  }

  export type AnnotationGroupByOutputType = {
    id: string
    jobId: string
    tenantId: string
    pageNum: number
    authorId: string | null
    authorEmail: string
    authorName: string | null
    fabricJson: JsonValue
    createdAt: Date
    updatedAt: Date
    _count: AnnotationCountAggregateOutputType | null
    _avg: AnnotationAvgAggregateOutputType | null
    _sum: AnnotationSumAggregateOutputType | null
    _min: AnnotationMinAggregateOutputType | null
    _max: AnnotationMaxAggregateOutputType | null
  }

  type GetAnnotationGroupByPayload<T extends AnnotationGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<AnnotationGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof AnnotationGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], AnnotationGroupByOutputType[P]>
            : GetScalarType<T[P], AnnotationGroupByOutputType[P]>
        }
      >
    >


  export type AnnotationSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    jobId?: boolean
    tenantId?: boolean
    pageNum?: boolean
    authorId?: boolean
    authorEmail?: boolean
    authorName?: boolean
    fabricJson?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["annotation"]>

  export type AnnotationSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    jobId?: boolean
    tenantId?: boolean
    pageNum?: boolean
    authorId?: boolean
    authorEmail?: boolean
    authorName?: boolean
    fabricJson?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["annotation"]>

  export type AnnotationSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    jobId?: boolean
    tenantId?: boolean
    pageNum?: boolean
    authorId?: boolean
    authorEmail?: boolean
    authorName?: boolean
    fabricJson?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["annotation"]>

  export type AnnotationSelectScalar = {
    id?: boolean
    jobId?: boolean
    tenantId?: boolean
    pageNum?: boolean
    authorId?: boolean
    authorEmail?: boolean
    authorName?: boolean
    fabricJson?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }

  export type AnnotationOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "jobId" | "tenantId" | "pageNum" | "authorId" | "authorEmail" | "authorName" | "fabricJson" | "createdAt" | "updatedAt", ExtArgs["result"]["annotation"]>
  export type AnnotationInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }
  export type AnnotationIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }
  export type AnnotationIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }

  export type $AnnotationPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Annotation"
    objects: {
      tenant: Prisma.$TenantPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      jobId: string
      tenantId: string
      pageNum: number
      authorId: string | null
      authorEmail: string
      authorName: string | null
      fabricJson: Prisma.JsonValue
      createdAt: Date
      updatedAt: Date
    }, ExtArgs["result"]["annotation"]>
    composites: {}
  }

  type AnnotationGetPayload<S extends boolean | null | undefined | AnnotationDefaultArgs> = $Result.GetResult<Prisma.$AnnotationPayload, S>

  type AnnotationCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<AnnotationFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: AnnotationCountAggregateInputType | true
    }

  export interface AnnotationDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Annotation'], meta: { name: 'Annotation' } }
    /**
     * Find zero or one Annotation that matches the filter.
     * @param {AnnotationFindUniqueArgs} args - Arguments to find a Annotation
     * @example
     * // Get one Annotation
     * const annotation = await prisma.annotation.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends AnnotationFindUniqueArgs>(args: SelectSubset<T, AnnotationFindUniqueArgs<ExtArgs>>): Prisma__AnnotationClient<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Annotation that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {AnnotationFindUniqueOrThrowArgs} args - Arguments to find a Annotation
     * @example
     * // Get one Annotation
     * const annotation = await prisma.annotation.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends AnnotationFindUniqueOrThrowArgs>(args: SelectSubset<T, AnnotationFindUniqueOrThrowArgs<ExtArgs>>): Prisma__AnnotationClient<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Annotation that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AnnotationFindFirstArgs} args - Arguments to find a Annotation
     * @example
     * // Get one Annotation
     * const annotation = await prisma.annotation.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends AnnotationFindFirstArgs>(args?: SelectSubset<T, AnnotationFindFirstArgs<ExtArgs>>): Prisma__AnnotationClient<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Annotation that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AnnotationFindFirstOrThrowArgs} args - Arguments to find a Annotation
     * @example
     * // Get one Annotation
     * const annotation = await prisma.annotation.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends AnnotationFindFirstOrThrowArgs>(args?: SelectSubset<T, AnnotationFindFirstOrThrowArgs<ExtArgs>>): Prisma__AnnotationClient<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Annotations that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AnnotationFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Annotations
     * const annotations = await prisma.annotation.findMany()
     * 
     * // Get first 10 Annotations
     * const annotations = await prisma.annotation.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const annotationWithIdOnly = await prisma.annotation.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends AnnotationFindManyArgs>(args?: SelectSubset<T, AnnotationFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Annotation.
     * @param {AnnotationCreateArgs} args - Arguments to create a Annotation.
     * @example
     * // Create one Annotation
     * const Annotation = await prisma.annotation.create({
     *   data: {
     *     // ... data to create a Annotation
     *   }
     * })
     * 
     */
    create<T extends AnnotationCreateArgs>(args: SelectSubset<T, AnnotationCreateArgs<ExtArgs>>): Prisma__AnnotationClient<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Annotations.
     * @param {AnnotationCreateManyArgs} args - Arguments to create many Annotations.
     * @example
     * // Create many Annotations
     * const annotation = await prisma.annotation.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends AnnotationCreateManyArgs>(args?: SelectSubset<T, AnnotationCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Annotations and returns the data saved in the database.
     * @param {AnnotationCreateManyAndReturnArgs} args - Arguments to create many Annotations.
     * @example
     * // Create many Annotations
     * const annotation = await prisma.annotation.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Annotations and only return the `id`
     * const annotationWithIdOnly = await prisma.annotation.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends AnnotationCreateManyAndReturnArgs>(args?: SelectSubset<T, AnnotationCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Annotation.
     * @param {AnnotationDeleteArgs} args - Arguments to delete one Annotation.
     * @example
     * // Delete one Annotation
     * const Annotation = await prisma.annotation.delete({
     *   where: {
     *     // ... filter to delete one Annotation
     *   }
     * })
     * 
     */
    delete<T extends AnnotationDeleteArgs>(args: SelectSubset<T, AnnotationDeleteArgs<ExtArgs>>): Prisma__AnnotationClient<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Annotation.
     * @param {AnnotationUpdateArgs} args - Arguments to update one Annotation.
     * @example
     * // Update one Annotation
     * const annotation = await prisma.annotation.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends AnnotationUpdateArgs>(args: SelectSubset<T, AnnotationUpdateArgs<ExtArgs>>): Prisma__AnnotationClient<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Annotations.
     * @param {AnnotationDeleteManyArgs} args - Arguments to filter Annotations to delete.
     * @example
     * // Delete a few Annotations
     * const { count } = await prisma.annotation.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends AnnotationDeleteManyArgs>(args?: SelectSubset<T, AnnotationDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Annotations.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AnnotationUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Annotations
     * const annotation = await prisma.annotation.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends AnnotationUpdateManyArgs>(args: SelectSubset<T, AnnotationUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Annotations and returns the data updated in the database.
     * @param {AnnotationUpdateManyAndReturnArgs} args - Arguments to update many Annotations.
     * @example
     * // Update many Annotations
     * const annotation = await prisma.annotation.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Annotations and only return the `id`
     * const annotationWithIdOnly = await prisma.annotation.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends AnnotationUpdateManyAndReturnArgs>(args: SelectSubset<T, AnnotationUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Annotation.
     * @param {AnnotationUpsertArgs} args - Arguments to update or create a Annotation.
     * @example
     * // Update or create a Annotation
     * const annotation = await prisma.annotation.upsert({
     *   create: {
     *     // ... data to create a Annotation
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Annotation we want to update
     *   }
     * })
     */
    upsert<T extends AnnotationUpsertArgs>(args: SelectSubset<T, AnnotationUpsertArgs<ExtArgs>>): Prisma__AnnotationClient<$Result.GetResult<Prisma.$AnnotationPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Annotations.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AnnotationCountArgs} args - Arguments to filter Annotations to count.
     * @example
     * // Count the number of Annotations
     * const count = await prisma.annotation.count({
     *   where: {
     *     // ... the filter for the Annotations we want to count
     *   }
     * })
    **/
    count<T extends AnnotationCountArgs>(
      args?: Subset<T, AnnotationCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], AnnotationCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Annotation.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AnnotationAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends AnnotationAggregateArgs>(args: Subset<T, AnnotationAggregateArgs>): Prisma.PrismaPromise<GetAnnotationAggregateType<T>>

    /**
     * Group by Annotation.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AnnotationGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends AnnotationGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: AnnotationGroupByArgs['orderBy'] }
        : { orderBy?: AnnotationGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, AnnotationGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetAnnotationGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Annotation model
   */
  readonly fields: AnnotationFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Annotation.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__AnnotationClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    tenant<T extends TenantDefaultArgs<ExtArgs> = {}>(args?: Subset<T, TenantDefaultArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Annotation model
   */
  interface AnnotationFieldRefs {
    readonly id: FieldRef<"Annotation", 'String'>
    readonly jobId: FieldRef<"Annotation", 'String'>
    readonly tenantId: FieldRef<"Annotation", 'String'>
    readonly pageNum: FieldRef<"Annotation", 'Int'>
    readonly authorId: FieldRef<"Annotation", 'String'>
    readonly authorEmail: FieldRef<"Annotation", 'String'>
    readonly authorName: FieldRef<"Annotation", 'String'>
    readonly fabricJson: FieldRef<"Annotation", 'Json'>
    readonly createdAt: FieldRef<"Annotation", 'DateTime'>
    readonly updatedAt: FieldRef<"Annotation", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * Annotation findUnique
   */
  export type AnnotationFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
    /**
     * Filter, which Annotation to fetch.
     */
    where: AnnotationWhereUniqueInput
  }

  /**
   * Annotation findUniqueOrThrow
   */
  export type AnnotationFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
    /**
     * Filter, which Annotation to fetch.
     */
    where: AnnotationWhereUniqueInput
  }

  /**
   * Annotation findFirst
   */
  export type AnnotationFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
    /**
     * Filter, which Annotation to fetch.
     */
    where?: AnnotationWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Annotations to fetch.
     */
    orderBy?: AnnotationOrderByWithRelationInput | AnnotationOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Annotations.
     */
    cursor?: AnnotationWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Annotations from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Annotations.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Annotations.
     */
    distinct?: AnnotationScalarFieldEnum | AnnotationScalarFieldEnum[]
  }

  /**
   * Annotation findFirstOrThrow
   */
  export type AnnotationFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
    /**
     * Filter, which Annotation to fetch.
     */
    where?: AnnotationWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Annotations to fetch.
     */
    orderBy?: AnnotationOrderByWithRelationInput | AnnotationOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Annotations.
     */
    cursor?: AnnotationWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Annotations from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Annotations.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Annotations.
     */
    distinct?: AnnotationScalarFieldEnum | AnnotationScalarFieldEnum[]
  }

  /**
   * Annotation findMany
   */
  export type AnnotationFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
    /**
     * Filter, which Annotations to fetch.
     */
    where?: AnnotationWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Annotations to fetch.
     */
    orderBy?: AnnotationOrderByWithRelationInput | AnnotationOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Annotations.
     */
    cursor?: AnnotationWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Annotations from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Annotations.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Annotations.
     */
    distinct?: AnnotationScalarFieldEnum | AnnotationScalarFieldEnum[]
  }

  /**
   * Annotation create
   */
  export type AnnotationCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
    /**
     * The data needed to create a Annotation.
     */
    data: XOR<AnnotationCreateInput, AnnotationUncheckedCreateInput>
  }

  /**
   * Annotation createMany
   */
  export type AnnotationCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Annotations.
     */
    data: AnnotationCreateManyInput | AnnotationCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Annotation createManyAndReturn
   */
  export type AnnotationCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * The data used to create many Annotations.
     */
    data: AnnotationCreateManyInput | AnnotationCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Annotation update
   */
  export type AnnotationUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
    /**
     * The data needed to update a Annotation.
     */
    data: XOR<AnnotationUpdateInput, AnnotationUncheckedUpdateInput>
    /**
     * Choose, which Annotation to update.
     */
    where: AnnotationWhereUniqueInput
  }

  /**
   * Annotation updateMany
   */
  export type AnnotationUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Annotations.
     */
    data: XOR<AnnotationUpdateManyMutationInput, AnnotationUncheckedUpdateManyInput>
    /**
     * Filter which Annotations to update
     */
    where?: AnnotationWhereInput
    /**
     * Limit how many Annotations to update.
     */
    limit?: number
  }

  /**
   * Annotation updateManyAndReturn
   */
  export type AnnotationUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * The data used to update Annotations.
     */
    data: XOR<AnnotationUpdateManyMutationInput, AnnotationUncheckedUpdateManyInput>
    /**
     * Filter which Annotations to update
     */
    where?: AnnotationWhereInput
    /**
     * Limit how many Annotations to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Annotation upsert
   */
  export type AnnotationUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
    /**
     * The filter to search for the Annotation to update in case it exists.
     */
    where: AnnotationWhereUniqueInput
    /**
     * In case the Annotation found by the `where` argument doesn't exist, create a new Annotation with this data.
     */
    create: XOR<AnnotationCreateInput, AnnotationUncheckedCreateInput>
    /**
     * In case the Annotation was found with the provided `where` argument, update it with this data.
     */
    update: XOR<AnnotationUpdateInput, AnnotationUncheckedUpdateInput>
  }

  /**
   * Annotation delete
   */
  export type AnnotationDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
    /**
     * Filter which Annotation to delete.
     */
    where: AnnotationWhereUniqueInput
  }

  /**
   * Annotation deleteMany
   */
  export type AnnotationDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Annotations to delete
     */
    where?: AnnotationWhereInput
    /**
     * Limit how many Annotations to delete.
     */
    limit?: number
  }

  /**
   * Annotation without action
   */
  export type AnnotationDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Annotation
     */
    select?: AnnotationSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Annotation
     */
    omit?: AnnotationOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AnnotationInclude<ExtArgs> | null
  }


  /**
   * Model ReportView
   */

  export type AggregateReportView = {
    _count: ReportViewCountAggregateOutputType | null
    _min: ReportViewMinAggregateOutputType | null
    _max: ReportViewMaxAggregateOutputType | null
  }

  export type ReportViewMinAggregateOutputType = {
    id: string | null
    jobId: string | null
    tenantId: string | null
    reportToken: string | null
    viewerEmail: string | null
    viewerName: string | null
    ipAddress: string | null
    userAgent: string | null
    viewedAt: Date | null
  }

  export type ReportViewMaxAggregateOutputType = {
    id: string | null
    jobId: string | null
    tenantId: string | null
    reportToken: string | null
    viewerEmail: string | null
    viewerName: string | null
    ipAddress: string | null
    userAgent: string | null
    viewedAt: Date | null
  }

  export type ReportViewCountAggregateOutputType = {
    id: number
    jobId: number
    tenantId: number
    reportToken: number
    viewerEmail: number
    viewerName: number
    ipAddress: number
    userAgent: number
    viewedAt: number
    _all: number
  }


  export type ReportViewMinAggregateInputType = {
    id?: true
    jobId?: true
    tenantId?: true
    reportToken?: true
    viewerEmail?: true
    viewerName?: true
    ipAddress?: true
    userAgent?: true
    viewedAt?: true
  }

  export type ReportViewMaxAggregateInputType = {
    id?: true
    jobId?: true
    tenantId?: true
    reportToken?: true
    viewerEmail?: true
    viewerName?: true
    ipAddress?: true
    userAgent?: true
    viewedAt?: true
  }

  export type ReportViewCountAggregateInputType = {
    id?: true
    jobId?: true
    tenantId?: true
    reportToken?: true
    viewerEmail?: true
    viewerName?: true
    ipAddress?: true
    userAgent?: true
    viewedAt?: true
    _all?: true
  }

  export type ReportViewAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which ReportView to aggregate.
     */
    where?: ReportViewWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of ReportViews to fetch.
     */
    orderBy?: ReportViewOrderByWithRelationInput | ReportViewOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: ReportViewWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` ReportViews from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` ReportViews.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned ReportViews
    **/
    _count?: true | ReportViewCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: ReportViewMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: ReportViewMaxAggregateInputType
  }

  export type GetReportViewAggregateType<T extends ReportViewAggregateArgs> = {
        [P in keyof T & keyof AggregateReportView]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateReportView[P]>
      : GetScalarType<T[P], AggregateReportView[P]>
  }




  export type ReportViewGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: ReportViewWhereInput
    orderBy?: ReportViewOrderByWithAggregationInput | ReportViewOrderByWithAggregationInput[]
    by: ReportViewScalarFieldEnum[] | ReportViewScalarFieldEnum
    having?: ReportViewScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: ReportViewCountAggregateInputType | true
    _min?: ReportViewMinAggregateInputType
    _max?: ReportViewMaxAggregateInputType
  }

  export type ReportViewGroupByOutputType = {
    id: string
    jobId: string
    tenantId: string
    reportToken: string
    viewerEmail: string | null
    viewerName: string | null
    ipAddress: string | null
    userAgent: string | null
    viewedAt: Date
    _count: ReportViewCountAggregateOutputType | null
    _min: ReportViewMinAggregateOutputType | null
    _max: ReportViewMaxAggregateOutputType | null
  }

  type GetReportViewGroupByPayload<T extends ReportViewGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<ReportViewGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof ReportViewGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], ReportViewGroupByOutputType[P]>
            : GetScalarType<T[P], ReportViewGroupByOutputType[P]>
        }
      >
    >


  export type ReportViewSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    jobId?: boolean
    tenantId?: boolean
    reportToken?: boolean
    viewerEmail?: boolean
    viewerName?: boolean
    ipAddress?: boolean
    userAgent?: boolean
    viewedAt?: boolean
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["reportView"]>

  export type ReportViewSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    jobId?: boolean
    tenantId?: boolean
    reportToken?: boolean
    viewerEmail?: boolean
    viewerName?: boolean
    ipAddress?: boolean
    userAgent?: boolean
    viewedAt?: boolean
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["reportView"]>

  export type ReportViewSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    jobId?: boolean
    tenantId?: boolean
    reportToken?: boolean
    viewerEmail?: boolean
    viewerName?: boolean
    ipAddress?: boolean
    userAgent?: boolean
    viewedAt?: boolean
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["reportView"]>

  export type ReportViewSelectScalar = {
    id?: boolean
    jobId?: boolean
    tenantId?: boolean
    reportToken?: boolean
    viewerEmail?: boolean
    viewerName?: boolean
    ipAddress?: boolean
    userAgent?: boolean
    viewedAt?: boolean
  }

  export type ReportViewOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "jobId" | "tenantId" | "reportToken" | "viewerEmail" | "viewerName" | "ipAddress" | "userAgent" | "viewedAt", ExtArgs["result"]["reportView"]>
  export type ReportViewInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }
  export type ReportViewIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }
  export type ReportViewIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    tenant?: boolean | TenantDefaultArgs<ExtArgs>
  }

  export type $ReportViewPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "ReportView"
    objects: {
      tenant: Prisma.$TenantPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      jobId: string
      tenantId: string
      reportToken: string
      viewerEmail: string | null
      viewerName: string | null
      ipAddress: string | null
      userAgent: string | null
      viewedAt: Date
    }, ExtArgs["result"]["reportView"]>
    composites: {}
  }

  type ReportViewGetPayload<S extends boolean | null | undefined | ReportViewDefaultArgs> = $Result.GetResult<Prisma.$ReportViewPayload, S>

  type ReportViewCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<ReportViewFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: ReportViewCountAggregateInputType | true
    }

  export interface ReportViewDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['ReportView'], meta: { name: 'ReportView' } }
    /**
     * Find zero or one ReportView that matches the filter.
     * @param {ReportViewFindUniqueArgs} args - Arguments to find a ReportView
     * @example
     * // Get one ReportView
     * const reportView = await prisma.reportView.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends ReportViewFindUniqueArgs>(args: SelectSubset<T, ReportViewFindUniqueArgs<ExtArgs>>): Prisma__ReportViewClient<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one ReportView that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {ReportViewFindUniqueOrThrowArgs} args - Arguments to find a ReportView
     * @example
     * // Get one ReportView
     * const reportView = await prisma.reportView.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends ReportViewFindUniqueOrThrowArgs>(args: SelectSubset<T, ReportViewFindUniqueOrThrowArgs<ExtArgs>>): Prisma__ReportViewClient<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first ReportView that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ReportViewFindFirstArgs} args - Arguments to find a ReportView
     * @example
     * // Get one ReportView
     * const reportView = await prisma.reportView.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends ReportViewFindFirstArgs>(args?: SelectSubset<T, ReportViewFindFirstArgs<ExtArgs>>): Prisma__ReportViewClient<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first ReportView that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ReportViewFindFirstOrThrowArgs} args - Arguments to find a ReportView
     * @example
     * // Get one ReportView
     * const reportView = await prisma.reportView.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends ReportViewFindFirstOrThrowArgs>(args?: SelectSubset<T, ReportViewFindFirstOrThrowArgs<ExtArgs>>): Prisma__ReportViewClient<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more ReportViews that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ReportViewFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all ReportViews
     * const reportViews = await prisma.reportView.findMany()
     * 
     * // Get first 10 ReportViews
     * const reportViews = await prisma.reportView.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const reportViewWithIdOnly = await prisma.reportView.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends ReportViewFindManyArgs>(args?: SelectSubset<T, ReportViewFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a ReportView.
     * @param {ReportViewCreateArgs} args - Arguments to create a ReportView.
     * @example
     * // Create one ReportView
     * const ReportView = await prisma.reportView.create({
     *   data: {
     *     // ... data to create a ReportView
     *   }
     * })
     * 
     */
    create<T extends ReportViewCreateArgs>(args: SelectSubset<T, ReportViewCreateArgs<ExtArgs>>): Prisma__ReportViewClient<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many ReportViews.
     * @param {ReportViewCreateManyArgs} args - Arguments to create many ReportViews.
     * @example
     * // Create many ReportViews
     * const reportView = await prisma.reportView.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends ReportViewCreateManyArgs>(args?: SelectSubset<T, ReportViewCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many ReportViews and returns the data saved in the database.
     * @param {ReportViewCreateManyAndReturnArgs} args - Arguments to create many ReportViews.
     * @example
     * // Create many ReportViews
     * const reportView = await prisma.reportView.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many ReportViews and only return the `id`
     * const reportViewWithIdOnly = await prisma.reportView.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends ReportViewCreateManyAndReturnArgs>(args?: SelectSubset<T, ReportViewCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a ReportView.
     * @param {ReportViewDeleteArgs} args - Arguments to delete one ReportView.
     * @example
     * // Delete one ReportView
     * const ReportView = await prisma.reportView.delete({
     *   where: {
     *     // ... filter to delete one ReportView
     *   }
     * })
     * 
     */
    delete<T extends ReportViewDeleteArgs>(args: SelectSubset<T, ReportViewDeleteArgs<ExtArgs>>): Prisma__ReportViewClient<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one ReportView.
     * @param {ReportViewUpdateArgs} args - Arguments to update one ReportView.
     * @example
     * // Update one ReportView
     * const reportView = await prisma.reportView.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends ReportViewUpdateArgs>(args: SelectSubset<T, ReportViewUpdateArgs<ExtArgs>>): Prisma__ReportViewClient<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more ReportViews.
     * @param {ReportViewDeleteManyArgs} args - Arguments to filter ReportViews to delete.
     * @example
     * // Delete a few ReportViews
     * const { count } = await prisma.reportView.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends ReportViewDeleteManyArgs>(args?: SelectSubset<T, ReportViewDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more ReportViews.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ReportViewUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many ReportViews
     * const reportView = await prisma.reportView.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends ReportViewUpdateManyArgs>(args: SelectSubset<T, ReportViewUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more ReportViews and returns the data updated in the database.
     * @param {ReportViewUpdateManyAndReturnArgs} args - Arguments to update many ReportViews.
     * @example
     * // Update many ReportViews
     * const reportView = await prisma.reportView.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more ReportViews and only return the `id`
     * const reportViewWithIdOnly = await prisma.reportView.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends ReportViewUpdateManyAndReturnArgs>(args: SelectSubset<T, ReportViewUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one ReportView.
     * @param {ReportViewUpsertArgs} args - Arguments to update or create a ReportView.
     * @example
     * // Update or create a ReportView
     * const reportView = await prisma.reportView.upsert({
     *   create: {
     *     // ... data to create a ReportView
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the ReportView we want to update
     *   }
     * })
     */
    upsert<T extends ReportViewUpsertArgs>(args: SelectSubset<T, ReportViewUpsertArgs<ExtArgs>>): Prisma__ReportViewClient<$Result.GetResult<Prisma.$ReportViewPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of ReportViews.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ReportViewCountArgs} args - Arguments to filter ReportViews to count.
     * @example
     * // Count the number of ReportViews
     * const count = await prisma.reportView.count({
     *   where: {
     *     // ... the filter for the ReportViews we want to count
     *   }
     * })
    **/
    count<T extends ReportViewCountArgs>(
      args?: Subset<T, ReportViewCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], ReportViewCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a ReportView.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ReportViewAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends ReportViewAggregateArgs>(args: Subset<T, ReportViewAggregateArgs>): Prisma.PrismaPromise<GetReportViewAggregateType<T>>

    /**
     * Group by ReportView.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ReportViewGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends ReportViewGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: ReportViewGroupByArgs['orderBy'] }
        : { orderBy?: ReportViewGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, ReportViewGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetReportViewGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the ReportView model
   */
  readonly fields: ReportViewFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for ReportView.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__ReportViewClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    tenant<T extends TenantDefaultArgs<ExtArgs> = {}>(args?: Subset<T, TenantDefaultArgs<ExtArgs>>): Prisma__TenantClient<$Result.GetResult<Prisma.$TenantPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the ReportView model
   */
  interface ReportViewFieldRefs {
    readonly id: FieldRef<"ReportView", 'String'>
    readonly jobId: FieldRef<"ReportView", 'String'>
    readonly tenantId: FieldRef<"ReportView", 'String'>
    readonly reportToken: FieldRef<"ReportView", 'String'>
    readonly viewerEmail: FieldRef<"ReportView", 'String'>
    readonly viewerName: FieldRef<"ReportView", 'String'>
    readonly ipAddress: FieldRef<"ReportView", 'String'>
    readonly userAgent: FieldRef<"ReportView", 'String'>
    readonly viewedAt: FieldRef<"ReportView", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * ReportView findUnique
   */
  export type ReportViewFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
    /**
     * Filter, which ReportView to fetch.
     */
    where: ReportViewWhereUniqueInput
  }

  /**
   * ReportView findUniqueOrThrow
   */
  export type ReportViewFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
    /**
     * Filter, which ReportView to fetch.
     */
    where: ReportViewWhereUniqueInput
  }

  /**
   * ReportView findFirst
   */
  export type ReportViewFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
    /**
     * Filter, which ReportView to fetch.
     */
    where?: ReportViewWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of ReportViews to fetch.
     */
    orderBy?: ReportViewOrderByWithRelationInput | ReportViewOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for ReportViews.
     */
    cursor?: ReportViewWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` ReportViews from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` ReportViews.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of ReportViews.
     */
    distinct?: ReportViewScalarFieldEnum | ReportViewScalarFieldEnum[]
  }

  /**
   * ReportView findFirstOrThrow
   */
  export type ReportViewFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
    /**
     * Filter, which ReportView to fetch.
     */
    where?: ReportViewWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of ReportViews to fetch.
     */
    orderBy?: ReportViewOrderByWithRelationInput | ReportViewOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for ReportViews.
     */
    cursor?: ReportViewWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` ReportViews from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` ReportViews.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of ReportViews.
     */
    distinct?: ReportViewScalarFieldEnum | ReportViewScalarFieldEnum[]
  }

  /**
   * ReportView findMany
   */
  export type ReportViewFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
    /**
     * Filter, which ReportViews to fetch.
     */
    where?: ReportViewWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of ReportViews to fetch.
     */
    orderBy?: ReportViewOrderByWithRelationInput | ReportViewOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing ReportViews.
     */
    cursor?: ReportViewWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` ReportViews from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` ReportViews.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of ReportViews.
     */
    distinct?: ReportViewScalarFieldEnum | ReportViewScalarFieldEnum[]
  }

  /**
   * ReportView create
   */
  export type ReportViewCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
    /**
     * The data needed to create a ReportView.
     */
    data: XOR<ReportViewCreateInput, ReportViewUncheckedCreateInput>
  }

  /**
   * ReportView createMany
   */
  export type ReportViewCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many ReportViews.
     */
    data: ReportViewCreateManyInput | ReportViewCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * ReportView createManyAndReturn
   */
  export type ReportViewCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * The data used to create many ReportViews.
     */
    data: ReportViewCreateManyInput | ReportViewCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * ReportView update
   */
  export type ReportViewUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
    /**
     * The data needed to update a ReportView.
     */
    data: XOR<ReportViewUpdateInput, ReportViewUncheckedUpdateInput>
    /**
     * Choose, which ReportView to update.
     */
    where: ReportViewWhereUniqueInput
  }

  /**
   * ReportView updateMany
   */
  export type ReportViewUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update ReportViews.
     */
    data: XOR<ReportViewUpdateManyMutationInput, ReportViewUncheckedUpdateManyInput>
    /**
     * Filter which ReportViews to update
     */
    where?: ReportViewWhereInput
    /**
     * Limit how many ReportViews to update.
     */
    limit?: number
  }

  /**
   * ReportView updateManyAndReturn
   */
  export type ReportViewUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * The data used to update ReportViews.
     */
    data: XOR<ReportViewUpdateManyMutationInput, ReportViewUncheckedUpdateManyInput>
    /**
     * Filter which ReportViews to update
     */
    where?: ReportViewWhereInput
    /**
     * Limit how many ReportViews to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * ReportView upsert
   */
  export type ReportViewUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
    /**
     * The filter to search for the ReportView to update in case it exists.
     */
    where: ReportViewWhereUniqueInput
    /**
     * In case the ReportView found by the `where` argument doesn't exist, create a new ReportView with this data.
     */
    create: XOR<ReportViewCreateInput, ReportViewUncheckedCreateInput>
    /**
     * In case the ReportView was found with the provided `where` argument, update it with this data.
     */
    update: XOR<ReportViewUpdateInput, ReportViewUncheckedUpdateInput>
  }

  /**
   * ReportView delete
   */
  export type ReportViewDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
    /**
     * Filter which ReportView to delete.
     */
    where: ReportViewWhereUniqueInput
  }

  /**
   * ReportView deleteMany
   */
  export type ReportViewDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which ReportViews to delete
     */
    where?: ReportViewWhereInput
    /**
     * Limit how many ReportViews to delete.
     */
    limit?: number
  }

  /**
   * ReportView without action
   */
  export type ReportViewDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ReportView
     */
    select?: ReportViewSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ReportView
     */
    omit?: ReportViewOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ReportViewInclude<ExtArgs> | null
  }


  /**
   * Enums
   */

  export const TransactionIsolationLevel: {
    ReadUncommitted: 'ReadUncommitted',
    ReadCommitted: 'ReadCommitted',
    RepeatableRead: 'RepeatableRead',
    Serializable: 'Serializable'
  };

  export type TransactionIsolationLevel = (typeof TransactionIsolationLevel)[keyof typeof TransactionIsolationLevel]


  export const TenantScalarFieldEnum: {
    id: 'id',
    name: 'name',
    slug: 'slug',
    domain: 'domain',
    engineTenantId: 'engineTenantId',
    settings: 'settings',
    status: 'status',
    createdAt: 'createdAt',
    updatedAt: 'updatedAt'
  };

  export type TenantScalarFieldEnum = (typeof TenantScalarFieldEnum)[keyof typeof TenantScalarFieldEnum]


  export const UserScalarFieldEnum: {
    id: 'id',
    email: 'email',
    name: 'name',
    avatarUrl: 'avatarUrl',
    isSuperAdmin: 'isSuperAdmin',
    createdAt: 'createdAt',
    updatedAt: 'updatedAt'
  };

  export type UserScalarFieldEnum = (typeof UserScalarFieldEnum)[keyof typeof UserScalarFieldEnum]


  export const TenantUserScalarFieldEnum: {
    id: 'id',
    userId: 'userId',
    tenantId: 'tenantId',
    role: 'role',
    joinedAt: 'joinedAt'
  };

  export type TenantUserScalarFieldEnum = (typeof TenantUserScalarFieldEnum)[keyof typeof TenantUserScalarFieldEnum]


  export const TenantInviteScalarFieldEnum: {
    id: 'id',
    tenantId: 'tenantId',
    email: 'email',
    role: 'role',
    token: 'token',
    expiresAt: 'expiresAt',
    usedAt: 'usedAt',
    acceptedAt: 'acceptedAt',
    revokedAt: 'revokedAt',
    createdAt: 'createdAt'
  };

  export type TenantInviteScalarFieldEnum = (typeof TenantInviteScalarFieldEnum)[keyof typeof TenantInviteScalarFieldEnum]


  export const SessionScalarFieldEnum: {
    id: 'id',
    userId: 'userId',
    token: 'token',
    expiresAt: 'expiresAt',
    createdAt: 'createdAt',
    ipAddress: 'ipAddress',
    userAgent: 'userAgent',
    impersonatingTenantId: 'impersonatingTenantId'
  };

  export type SessionScalarFieldEnum = (typeof SessionScalarFieldEnum)[keyof typeof SessionScalarFieldEnum]


  export const MagicLinkScalarFieldEnum: {
    id: 'id',
    userId: 'userId',
    token: 'token',
    pollingToken: 'pollingToken',
    code: 'code',
    ipAddress: 'ipAddress',
    expiresAt: 'expiresAt',
    usedAt: 'usedAt',
    createdAt: 'createdAt'
  };

  export type MagicLinkScalarFieldEnum = (typeof MagicLinkScalarFieldEnum)[keyof typeof MagicLinkScalarFieldEnum]


  export const AppSettingsScalarFieldEnum: {
    id: 'id',
    brandName: 'brandName',
    brandLogoUrl: 'brandLogoUrl',
    brandLogoUrlDark: 'brandLogoUrlDark',
    brandTagline: 'brandTagline',
    customCss: 'customCss',
    primaryColor: 'primaryColor',
    accentColor: 'accentColor',
    emailButtonColor: 'emailButtonColor',
    loginBgColor: 'loginBgColor',
    loginCardColor: 'loginCardColor',
    loginTextColor: 'loginTextColor',
    loginInputColor: 'loginInputColor',
    loginRingColor: 'loginRingColor',
    loginBgColorDark: 'loginBgColorDark',
    loginCardColorDark: 'loginCardColorDark',
    loginTextColorDark: 'loginTextColorDark',
    loginInputColorDark: 'loginInputColorDark',
    loginRingColorDark: 'loginRingColorDark',
    sidebarBgColor: 'sidebarBgColor',
    sidebarTextColor: 'sidebarTextColor',
    sidebarAccentColor: 'sidebarAccentColor',
    faviconUrl: 'faviconUrl',
    loginHeading: 'loginHeading',
    loginSubheading: 'loginSubheading',
    disabledPlugins: 'disabledPlugins',
    updatedAt: 'updatedAt'
  };

  export type AppSettingsScalarFieldEnum = (typeof AppSettingsScalarFieldEnum)[keyof typeof AppSettingsScalarFieldEnum]


  export const AuditLogScalarFieldEnum: {
    id: 'id',
    tenantId: 'tenantId',
    userId: 'userId',
    action: 'action',
    entity: 'entity',
    entityId: 'entityId',
    metadata: 'metadata',
    ipAddress: 'ipAddress',
    createdAt: 'createdAt',
    impersonatedBy: 'impersonatedBy'
  };

  export type AuditLogScalarFieldEnum = (typeof AuditLogScalarFieldEnum)[keyof typeof AuditLogScalarFieldEnum]


  export const WaitlistEntryScalarFieldEnum: {
    id: 'id',
    email: 'email',
    name: 'name',
    company: 'company',
    useCase: 'useCase',
    status: 'status',
    promotedAt: 'promotedAt',
    createdAt: 'createdAt'
  };

  export type WaitlistEntryScalarFieldEnum = (typeof WaitlistEntryScalarFieldEnum)[keyof typeof WaitlistEntryScalarFieldEnum]


  export const AnnotationScalarFieldEnum: {
    id: 'id',
    jobId: 'jobId',
    tenantId: 'tenantId',
    pageNum: 'pageNum',
    authorId: 'authorId',
    authorEmail: 'authorEmail',
    authorName: 'authorName',
    fabricJson: 'fabricJson',
    createdAt: 'createdAt',
    updatedAt: 'updatedAt'
  };

  export type AnnotationScalarFieldEnum = (typeof AnnotationScalarFieldEnum)[keyof typeof AnnotationScalarFieldEnum]


  export const ReportViewScalarFieldEnum: {
    id: 'id',
    jobId: 'jobId',
    tenantId: 'tenantId',
    reportToken: 'reportToken',
    viewerEmail: 'viewerEmail',
    viewerName: 'viewerName',
    ipAddress: 'ipAddress',
    userAgent: 'userAgent',
    viewedAt: 'viewedAt'
  };

  export type ReportViewScalarFieldEnum = (typeof ReportViewScalarFieldEnum)[keyof typeof ReportViewScalarFieldEnum]


  export const SortOrder: {
    asc: 'asc',
    desc: 'desc'
  };

  export type SortOrder = (typeof SortOrder)[keyof typeof SortOrder]


  export const JsonNullValueInput: {
    JsonNull: typeof JsonNull
  };

  export type JsonNullValueInput = (typeof JsonNullValueInput)[keyof typeof JsonNullValueInput]


  export const QueryMode: {
    default: 'default',
    insensitive: 'insensitive'
  };

  export type QueryMode = (typeof QueryMode)[keyof typeof QueryMode]


  export const JsonNullValueFilter: {
    DbNull: typeof DbNull,
    JsonNull: typeof JsonNull,
    AnyNull: typeof AnyNull
  };

  export type JsonNullValueFilter = (typeof JsonNullValueFilter)[keyof typeof JsonNullValueFilter]


  export const NullsOrder: {
    first: 'first',
    last: 'last'
  };

  export type NullsOrder = (typeof NullsOrder)[keyof typeof NullsOrder]


  /**
   * Field references
   */


  /**
   * Reference to a field of type 'String'
   */
  export type StringFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'String'>
    


  /**
   * Reference to a field of type 'String[]'
   */
  export type ListStringFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'String[]'>
    


  /**
   * Reference to a field of type 'Json'
   */
  export type JsonFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Json'>
    


  /**
   * Reference to a field of type 'QueryMode'
   */
  export type EnumQueryModeFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'QueryMode'>
    


  /**
   * Reference to a field of type 'TenantStatus'
   */
  export type EnumTenantStatusFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'TenantStatus'>
    


  /**
   * Reference to a field of type 'TenantStatus[]'
   */
  export type ListEnumTenantStatusFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'TenantStatus[]'>
    


  /**
   * Reference to a field of type 'DateTime'
   */
  export type DateTimeFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'DateTime'>
    


  /**
   * Reference to a field of type 'DateTime[]'
   */
  export type ListDateTimeFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'DateTime[]'>
    


  /**
   * Reference to a field of type 'Boolean'
   */
  export type BooleanFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Boolean'>
    


  /**
   * Reference to a field of type 'TenantRole'
   */
  export type EnumTenantRoleFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'TenantRole'>
    


  /**
   * Reference to a field of type 'TenantRole[]'
   */
  export type ListEnumTenantRoleFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'TenantRole[]'>
    


  /**
   * Reference to a field of type 'WaitlistStatus'
   */
  export type EnumWaitlistStatusFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'WaitlistStatus'>
    


  /**
   * Reference to a field of type 'WaitlistStatus[]'
   */
  export type ListEnumWaitlistStatusFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'WaitlistStatus[]'>
    


  /**
   * Reference to a field of type 'Int'
   */
  export type IntFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Int'>
    


  /**
   * Reference to a field of type 'Int[]'
   */
  export type ListIntFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Int[]'>
    


  /**
   * Reference to a field of type 'Float'
   */
  export type FloatFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Float'>
    


  /**
   * Reference to a field of type 'Float[]'
   */
  export type ListFloatFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Float[]'>
    
  /**
   * Deep Input Types
   */


  export type TenantWhereInput = {
    AND?: TenantWhereInput | TenantWhereInput[]
    OR?: TenantWhereInput[]
    NOT?: TenantWhereInput | TenantWhereInput[]
    id?: StringFilter<"Tenant"> | string
    name?: StringFilter<"Tenant"> | string
    slug?: StringFilter<"Tenant"> | string
    domain?: StringNullableFilter<"Tenant"> | string | null
    engineTenantId?: StringNullableFilter<"Tenant"> | string | null
    settings?: JsonFilter<"Tenant">
    status?: EnumTenantStatusFilter<"Tenant"> | $Enums.TenantStatus
    createdAt?: DateTimeFilter<"Tenant"> | Date | string
    updatedAt?: DateTimeFilter<"Tenant"> | Date | string
    users?: TenantUserListRelationFilter
    invites?: TenantInviteListRelationFilter
    annotations?: AnnotationListRelationFilter
    reportViews?: ReportViewListRelationFilter
  }

  export type TenantOrderByWithRelationInput = {
    id?: SortOrder
    name?: SortOrder
    slug?: SortOrder
    domain?: SortOrderInput | SortOrder
    engineTenantId?: SortOrderInput | SortOrder
    settings?: SortOrder
    status?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    users?: TenantUserOrderByRelationAggregateInput
    invites?: TenantInviteOrderByRelationAggregateInput
    annotations?: AnnotationOrderByRelationAggregateInput
    reportViews?: ReportViewOrderByRelationAggregateInput
  }

  export type TenantWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    slug?: string
    domain?: string
    AND?: TenantWhereInput | TenantWhereInput[]
    OR?: TenantWhereInput[]
    NOT?: TenantWhereInput | TenantWhereInput[]
    name?: StringFilter<"Tenant"> | string
    engineTenantId?: StringNullableFilter<"Tenant"> | string | null
    settings?: JsonFilter<"Tenant">
    status?: EnumTenantStatusFilter<"Tenant"> | $Enums.TenantStatus
    createdAt?: DateTimeFilter<"Tenant"> | Date | string
    updatedAt?: DateTimeFilter<"Tenant"> | Date | string
    users?: TenantUserListRelationFilter
    invites?: TenantInviteListRelationFilter
    annotations?: AnnotationListRelationFilter
    reportViews?: ReportViewListRelationFilter
  }, "id" | "slug" | "domain">

  export type TenantOrderByWithAggregationInput = {
    id?: SortOrder
    name?: SortOrder
    slug?: SortOrder
    domain?: SortOrderInput | SortOrder
    engineTenantId?: SortOrderInput | SortOrder
    settings?: SortOrder
    status?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    _count?: TenantCountOrderByAggregateInput
    _max?: TenantMaxOrderByAggregateInput
    _min?: TenantMinOrderByAggregateInput
  }

  export type TenantScalarWhereWithAggregatesInput = {
    AND?: TenantScalarWhereWithAggregatesInput | TenantScalarWhereWithAggregatesInput[]
    OR?: TenantScalarWhereWithAggregatesInput[]
    NOT?: TenantScalarWhereWithAggregatesInput | TenantScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Tenant"> | string
    name?: StringWithAggregatesFilter<"Tenant"> | string
    slug?: StringWithAggregatesFilter<"Tenant"> | string
    domain?: StringNullableWithAggregatesFilter<"Tenant"> | string | null
    engineTenantId?: StringNullableWithAggregatesFilter<"Tenant"> | string | null
    settings?: JsonWithAggregatesFilter<"Tenant">
    status?: EnumTenantStatusWithAggregatesFilter<"Tenant"> | $Enums.TenantStatus
    createdAt?: DateTimeWithAggregatesFilter<"Tenant"> | Date | string
    updatedAt?: DateTimeWithAggregatesFilter<"Tenant"> | Date | string
  }

  export type UserWhereInput = {
    AND?: UserWhereInput | UserWhereInput[]
    OR?: UserWhereInput[]
    NOT?: UserWhereInput | UserWhereInput[]
    id?: StringFilter<"User"> | string
    email?: StringFilter<"User"> | string
    name?: StringNullableFilter<"User"> | string | null
    avatarUrl?: StringNullableFilter<"User"> | string | null
    isSuperAdmin?: BoolFilter<"User"> | boolean
    createdAt?: DateTimeFilter<"User"> | Date | string
    updatedAt?: DateTimeFilter<"User"> | Date | string
    tenants?: TenantUserListRelationFilter
    sessions?: SessionListRelationFilter
    magicLinks?: MagicLinkListRelationFilter
    invites?: TenantInviteListRelationFilter
  }

  export type UserOrderByWithRelationInput = {
    id?: SortOrder
    email?: SortOrder
    name?: SortOrderInput | SortOrder
    avatarUrl?: SortOrderInput | SortOrder
    isSuperAdmin?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    tenants?: TenantUserOrderByRelationAggregateInput
    sessions?: SessionOrderByRelationAggregateInput
    magicLinks?: MagicLinkOrderByRelationAggregateInput
    invites?: TenantInviteOrderByRelationAggregateInput
  }

  export type UserWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    email?: string
    AND?: UserWhereInput | UserWhereInput[]
    OR?: UserWhereInput[]
    NOT?: UserWhereInput | UserWhereInput[]
    name?: StringNullableFilter<"User"> | string | null
    avatarUrl?: StringNullableFilter<"User"> | string | null
    isSuperAdmin?: BoolFilter<"User"> | boolean
    createdAt?: DateTimeFilter<"User"> | Date | string
    updatedAt?: DateTimeFilter<"User"> | Date | string
    tenants?: TenantUserListRelationFilter
    sessions?: SessionListRelationFilter
    magicLinks?: MagicLinkListRelationFilter
    invites?: TenantInviteListRelationFilter
  }, "id" | "email">

  export type UserOrderByWithAggregationInput = {
    id?: SortOrder
    email?: SortOrder
    name?: SortOrderInput | SortOrder
    avatarUrl?: SortOrderInput | SortOrder
    isSuperAdmin?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    _count?: UserCountOrderByAggregateInput
    _max?: UserMaxOrderByAggregateInput
    _min?: UserMinOrderByAggregateInput
  }

  export type UserScalarWhereWithAggregatesInput = {
    AND?: UserScalarWhereWithAggregatesInput | UserScalarWhereWithAggregatesInput[]
    OR?: UserScalarWhereWithAggregatesInput[]
    NOT?: UserScalarWhereWithAggregatesInput | UserScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"User"> | string
    email?: StringWithAggregatesFilter<"User"> | string
    name?: StringNullableWithAggregatesFilter<"User"> | string | null
    avatarUrl?: StringNullableWithAggregatesFilter<"User"> | string | null
    isSuperAdmin?: BoolWithAggregatesFilter<"User"> | boolean
    createdAt?: DateTimeWithAggregatesFilter<"User"> | Date | string
    updatedAt?: DateTimeWithAggregatesFilter<"User"> | Date | string
  }

  export type TenantUserWhereInput = {
    AND?: TenantUserWhereInput | TenantUserWhereInput[]
    OR?: TenantUserWhereInput[]
    NOT?: TenantUserWhereInput | TenantUserWhereInput[]
    id?: StringFilter<"TenantUser"> | string
    userId?: StringFilter<"TenantUser"> | string
    tenantId?: StringFilter<"TenantUser"> | string
    role?: EnumTenantRoleFilter<"TenantUser"> | $Enums.TenantRole
    joinedAt?: DateTimeFilter<"TenantUser"> | Date | string
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
    tenant?: XOR<TenantScalarRelationFilter, TenantWhereInput>
  }

  export type TenantUserOrderByWithRelationInput = {
    id?: SortOrder
    userId?: SortOrder
    tenantId?: SortOrder
    role?: SortOrder
    joinedAt?: SortOrder
    user?: UserOrderByWithRelationInput
    tenant?: TenantOrderByWithRelationInput
  }

  export type TenantUserWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    userId_tenantId?: TenantUserUserIdTenantIdCompoundUniqueInput
    AND?: TenantUserWhereInput | TenantUserWhereInput[]
    OR?: TenantUserWhereInput[]
    NOT?: TenantUserWhereInput | TenantUserWhereInput[]
    userId?: StringFilter<"TenantUser"> | string
    tenantId?: StringFilter<"TenantUser"> | string
    role?: EnumTenantRoleFilter<"TenantUser"> | $Enums.TenantRole
    joinedAt?: DateTimeFilter<"TenantUser"> | Date | string
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
    tenant?: XOR<TenantScalarRelationFilter, TenantWhereInput>
  }, "id" | "userId_tenantId">

  export type TenantUserOrderByWithAggregationInput = {
    id?: SortOrder
    userId?: SortOrder
    tenantId?: SortOrder
    role?: SortOrder
    joinedAt?: SortOrder
    _count?: TenantUserCountOrderByAggregateInput
    _max?: TenantUserMaxOrderByAggregateInput
    _min?: TenantUserMinOrderByAggregateInput
  }

  export type TenantUserScalarWhereWithAggregatesInput = {
    AND?: TenantUserScalarWhereWithAggregatesInput | TenantUserScalarWhereWithAggregatesInput[]
    OR?: TenantUserScalarWhereWithAggregatesInput[]
    NOT?: TenantUserScalarWhereWithAggregatesInput | TenantUserScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"TenantUser"> | string
    userId?: StringWithAggregatesFilter<"TenantUser"> | string
    tenantId?: StringWithAggregatesFilter<"TenantUser"> | string
    role?: EnumTenantRoleWithAggregatesFilter<"TenantUser"> | $Enums.TenantRole
    joinedAt?: DateTimeWithAggregatesFilter<"TenantUser"> | Date | string
  }

  export type TenantInviteWhereInput = {
    AND?: TenantInviteWhereInput | TenantInviteWhereInput[]
    OR?: TenantInviteWhereInput[]
    NOT?: TenantInviteWhereInput | TenantInviteWhereInput[]
    id?: StringFilter<"TenantInvite"> | string
    tenantId?: StringFilter<"TenantInvite"> | string
    email?: StringFilter<"TenantInvite"> | string
    role?: EnumTenantRoleFilter<"TenantInvite"> | $Enums.TenantRole
    token?: StringFilter<"TenantInvite"> | string
    expiresAt?: DateTimeFilter<"TenantInvite"> | Date | string
    usedAt?: DateTimeNullableFilter<"TenantInvite"> | Date | string | null
    acceptedAt?: DateTimeNullableFilter<"TenantInvite"> | Date | string | null
    revokedAt?: DateTimeNullableFilter<"TenantInvite"> | Date | string | null
    createdAt?: DateTimeFilter<"TenantInvite"> | Date | string
    tenant?: XOR<TenantScalarRelationFilter, TenantWhereInput>
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
  }

  export type TenantInviteOrderByWithRelationInput = {
    id?: SortOrder
    tenantId?: SortOrder
    email?: SortOrder
    role?: SortOrder
    token?: SortOrder
    expiresAt?: SortOrder
    usedAt?: SortOrderInput | SortOrder
    acceptedAt?: SortOrderInput | SortOrder
    revokedAt?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    tenant?: TenantOrderByWithRelationInput
    user?: UserOrderByWithRelationInput
  }

  export type TenantInviteWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    token?: string
    tenantId_email?: TenantInviteTenantIdEmailCompoundUniqueInput
    AND?: TenantInviteWhereInput | TenantInviteWhereInput[]
    OR?: TenantInviteWhereInput[]
    NOT?: TenantInviteWhereInput | TenantInviteWhereInput[]
    tenantId?: StringFilter<"TenantInvite"> | string
    email?: StringFilter<"TenantInvite"> | string
    role?: EnumTenantRoleFilter<"TenantInvite"> | $Enums.TenantRole
    expiresAt?: DateTimeFilter<"TenantInvite"> | Date | string
    usedAt?: DateTimeNullableFilter<"TenantInvite"> | Date | string | null
    acceptedAt?: DateTimeNullableFilter<"TenantInvite"> | Date | string | null
    revokedAt?: DateTimeNullableFilter<"TenantInvite"> | Date | string | null
    createdAt?: DateTimeFilter<"TenantInvite"> | Date | string
    tenant?: XOR<TenantScalarRelationFilter, TenantWhereInput>
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
  }, "id" | "token" | "tenantId_email">

  export type TenantInviteOrderByWithAggregationInput = {
    id?: SortOrder
    tenantId?: SortOrder
    email?: SortOrder
    role?: SortOrder
    token?: SortOrder
    expiresAt?: SortOrder
    usedAt?: SortOrderInput | SortOrder
    acceptedAt?: SortOrderInput | SortOrder
    revokedAt?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    _count?: TenantInviteCountOrderByAggregateInput
    _max?: TenantInviteMaxOrderByAggregateInput
    _min?: TenantInviteMinOrderByAggregateInput
  }

  export type TenantInviteScalarWhereWithAggregatesInput = {
    AND?: TenantInviteScalarWhereWithAggregatesInput | TenantInviteScalarWhereWithAggregatesInput[]
    OR?: TenantInviteScalarWhereWithAggregatesInput[]
    NOT?: TenantInviteScalarWhereWithAggregatesInput | TenantInviteScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"TenantInvite"> | string
    tenantId?: StringWithAggregatesFilter<"TenantInvite"> | string
    email?: StringWithAggregatesFilter<"TenantInvite"> | string
    role?: EnumTenantRoleWithAggregatesFilter<"TenantInvite"> | $Enums.TenantRole
    token?: StringWithAggregatesFilter<"TenantInvite"> | string
    expiresAt?: DateTimeWithAggregatesFilter<"TenantInvite"> | Date | string
    usedAt?: DateTimeNullableWithAggregatesFilter<"TenantInvite"> | Date | string | null
    acceptedAt?: DateTimeNullableWithAggregatesFilter<"TenantInvite"> | Date | string | null
    revokedAt?: DateTimeNullableWithAggregatesFilter<"TenantInvite"> | Date | string | null
    createdAt?: DateTimeWithAggregatesFilter<"TenantInvite"> | Date | string
  }

  export type SessionWhereInput = {
    AND?: SessionWhereInput | SessionWhereInput[]
    OR?: SessionWhereInput[]
    NOT?: SessionWhereInput | SessionWhereInput[]
    id?: StringFilter<"Session"> | string
    userId?: StringFilter<"Session"> | string
    token?: StringFilter<"Session"> | string
    expiresAt?: DateTimeFilter<"Session"> | Date | string
    createdAt?: DateTimeFilter<"Session"> | Date | string
    ipAddress?: StringNullableFilter<"Session"> | string | null
    userAgent?: StringNullableFilter<"Session"> | string | null
    impersonatingTenantId?: StringNullableFilter<"Session"> | string | null
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
  }

  export type SessionOrderByWithRelationInput = {
    id?: SortOrder
    userId?: SortOrder
    token?: SortOrder
    expiresAt?: SortOrder
    createdAt?: SortOrder
    ipAddress?: SortOrderInput | SortOrder
    userAgent?: SortOrderInput | SortOrder
    impersonatingTenantId?: SortOrderInput | SortOrder
    user?: UserOrderByWithRelationInput
  }

  export type SessionWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    token?: string
    AND?: SessionWhereInput | SessionWhereInput[]
    OR?: SessionWhereInput[]
    NOT?: SessionWhereInput | SessionWhereInput[]
    userId?: StringFilter<"Session"> | string
    expiresAt?: DateTimeFilter<"Session"> | Date | string
    createdAt?: DateTimeFilter<"Session"> | Date | string
    ipAddress?: StringNullableFilter<"Session"> | string | null
    userAgent?: StringNullableFilter<"Session"> | string | null
    impersonatingTenantId?: StringNullableFilter<"Session"> | string | null
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
  }, "id" | "token">

  export type SessionOrderByWithAggregationInput = {
    id?: SortOrder
    userId?: SortOrder
    token?: SortOrder
    expiresAt?: SortOrder
    createdAt?: SortOrder
    ipAddress?: SortOrderInput | SortOrder
    userAgent?: SortOrderInput | SortOrder
    impersonatingTenantId?: SortOrderInput | SortOrder
    _count?: SessionCountOrderByAggregateInput
    _max?: SessionMaxOrderByAggregateInput
    _min?: SessionMinOrderByAggregateInput
  }

  export type SessionScalarWhereWithAggregatesInput = {
    AND?: SessionScalarWhereWithAggregatesInput | SessionScalarWhereWithAggregatesInput[]
    OR?: SessionScalarWhereWithAggregatesInput[]
    NOT?: SessionScalarWhereWithAggregatesInput | SessionScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Session"> | string
    userId?: StringWithAggregatesFilter<"Session"> | string
    token?: StringWithAggregatesFilter<"Session"> | string
    expiresAt?: DateTimeWithAggregatesFilter<"Session"> | Date | string
    createdAt?: DateTimeWithAggregatesFilter<"Session"> | Date | string
    ipAddress?: StringNullableWithAggregatesFilter<"Session"> | string | null
    userAgent?: StringNullableWithAggregatesFilter<"Session"> | string | null
    impersonatingTenantId?: StringNullableWithAggregatesFilter<"Session"> | string | null
  }

  export type MagicLinkWhereInput = {
    AND?: MagicLinkWhereInput | MagicLinkWhereInput[]
    OR?: MagicLinkWhereInput[]
    NOT?: MagicLinkWhereInput | MagicLinkWhereInput[]
    id?: StringFilter<"MagicLink"> | string
    userId?: StringFilter<"MagicLink"> | string
    token?: StringFilter<"MagicLink"> | string
    pollingToken?: StringNullableFilter<"MagicLink"> | string | null
    code?: StringNullableFilter<"MagicLink"> | string | null
    ipAddress?: StringNullableFilter<"MagicLink"> | string | null
    expiresAt?: DateTimeFilter<"MagicLink"> | Date | string
    usedAt?: DateTimeNullableFilter<"MagicLink"> | Date | string | null
    createdAt?: DateTimeFilter<"MagicLink"> | Date | string
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
  }

  export type MagicLinkOrderByWithRelationInput = {
    id?: SortOrder
    userId?: SortOrder
    token?: SortOrder
    pollingToken?: SortOrderInput | SortOrder
    code?: SortOrderInput | SortOrder
    ipAddress?: SortOrderInput | SortOrder
    expiresAt?: SortOrder
    usedAt?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    user?: UserOrderByWithRelationInput
  }

  export type MagicLinkWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    token?: string
    pollingToken?: string
    AND?: MagicLinkWhereInput | MagicLinkWhereInput[]
    OR?: MagicLinkWhereInput[]
    NOT?: MagicLinkWhereInput | MagicLinkWhereInput[]
    userId?: StringFilter<"MagicLink"> | string
    code?: StringNullableFilter<"MagicLink"> | string | null
    ipAddress?: StringNullableFilter<"MagicLink"> | string | null
    expiresAt?: DateTimeFilter<"MagicLink"> | Date | string
    usedAt?: DateTimeNullableFilter<"MagicLink"> | Date | string | null
    createdAt?: DateTimeFilter<"MagicLink"> | Date | string
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
  }, "id" | "token" | "pollingToken">

  export type MagicLinkOrderByWithAggregationInput = {
    id?: SortOrder
    userId?: SortOrder
    token?: SortOrder
    pollingToken?: SortOrderInput | SortOrder
    code?: SortOrderInput | SortOrder
    ipAddress?: SortOrderInput | SortOrder
    expiresAt?: SortOrder
    usedAt?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    _count?: MagicLinkCountOrderByAggregateInput
    _max?: MagicLinkMaxOrderByAggregateInput
    _min?: MagicLinkMinOrderByAggregateInput
  }

  export type MagicLinkScalarWhereWithAggregatesInput = {
    AND?: MagicLinkScalarWhereWithAggregatesInput | MagicLinkScalarWhereWithAggregatesInput[]
    OR?: MagicLinkScalarWhereWithAggregatesInput[]
    NOT?: MagicLinkScalarWhereWithAggregatesInput | MagicLinkScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"MagicLink"> | string
    userId?: StringWithAggregatesFilter<"MagicLink"> | string
    token?: StringWithAggregatesFilter<"MagicLink"> | string
    pollingToken?: StringNullableWithAggregatesFilter<"MagicLink"> | string | null
    code?: StringNullableWithAggregatesFilter<"MagicLink"> | string | null
    ipAddress?: StringNullableWithAggregatesFilter<"MagicLink"> | string | null
    expiresAt?: DateTimeWithAggregatesFilter<"MagicLink"> | Date | string
    usedAt?: DateTimeNullableWithAggregatesFilter<"MagicLink"> | Date | string | null
    createdAt?: DateTimeWithAggregatesFilter<"MagicLink"> | Date | string
  }

  export type AppSettingsWhereInput = {
    AND?: AppSettingsWhereInput | AppSettingsWhereInput[]
    OR?: AppSettingsWhereInput[]
    NOT?: AppSettingsWhereInput | AppSettingsWhereInput[]
    id?: StringFilter<"AppSettings"> | string
    brandName?: StringNullableFilter<"AppSettings"> | string | null
    brandLogoUrl?: StringNullableFilter<"AppSettings"> | string | null
    brandLogoUrlDark?: StringNullableFilter<"AppSettings"> | string | null
    brandTagline?: StringNullableFilter<"AppSettings"> | string | null
    customCss?: StringNullableFilter<"AppSettings"> | string | null
    primaryColor?: StringNullableFilter<"AppSettings"> | string | null
    accentColor?: StringNullableFilter<"AppSettings"> | string | null
    emailButtonColor?: StringNullableFilter<"AppSettings"> | string | null
    loginBgColor?: StringNullableFilter<"AppSettings"> | string | null
    loginCardColor?: StringNullableFilter<"AppSettings"> | string | null
    loginTextColor?: StringNullableFilter<"AppSettings"> | string | null
    loginInputColor?: StringNullableFilter<"AppSettings"> | string | null
    loginRingColor?: StringNullableFilter<"AppSettings"> | string | null
    loginBgColorDark?: StringNullableFilter<"AppSettings"> | string | null
    loginCardColorDark?: StringNullableFilter<"AppSettings"> | string | null
    loginTextColorDark?: StringNullableFilter<"AppSettings"> | string | null
    loginInputColorDark?: StringNullableFilter<"AppSettings"> | string | null
    loginRingColorDark?: StringNullableFilter<"AppSettings"> | string | null
    sidebarBgColor?: StringNullableFilter<"AppSettings"> | string | null
    sidebarTextColor?: StringNullableFilter<"AppSettings"> | string | null
    sidebarAccentColor?: StringNullableFilter<"AppSettings"> | string | null
    faviconUrl?: StringNullableFilter<"AppSettings"> | string | null
    loginHeading?: StringNullableFilter<"AppSettings"> | string | null
    loginSubheading?: StringNullableFilter<"AppSettings"> | string | null
    disabledPlugins?: StringNullableFilter<"AppSettings"> | string | null
    updatedAt?: DateTimeFilter<"AppSettings"> | Date | string
  }

  export type AppSettingsOrderByWithRelationInput = {
    id?: SortOrder
    brandName?: SortOrderInput | SortOrder
    brandLogoUrl?: SortOrderInput | SortOrder
    brandLogoUrlDark?: SortOrderInput | SortOrder
    brandTagline?: SortOrderInput | SortOrder
    customCss?: SortOrderInput | SortOrder
    primaryColor?: SortOrderInput | SortOrder
    accentColor?: SortOrderInput | SortOrder
    emailButtonColor?: SortOrderInput | SortOrder
    loginBgColor?: SortOrderInput | SortOrder
    loginCardColor?: SortOrderInput | SortOrder
    loginTextColor?: SortOrderInput | SortOrder
    loginInputColor?: SortOrderInput | SortOrder
    loginRingColor?: SortOrderInput | SortOrder
    loginBgColorDark?: SortOrderInput | SortOrder
    loginCardColorDark?: SortOrderInput | SortOrder
    loginTextColorDark?: SortOrderInput | SortOrder
    loginInputColorDark?: SortOrderInput | SortOrder
    loginRingColorDark?: SortOrderInput | SortOrder
    sidebarBgColor?: SortOrderInput | SortOrder
    sidebarTextColor?: SortOrderInput | SortOrder
    sidebarAccentColor?: SortOrderInput | SortOrder
    faviconUrl?: SortOrderInput | SortOrder
    loginHeading?: SortOrderInput | SortOrder
    loginSubheading?: SortOrderInput | SortOrder
    disabledPlugins?: SortOrderInput | SortOrder
    updatedAt?: SortOrder
  }

  export type AppSettingsWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: AppSettingsWhereInput | AppSettingsWhereInput[]
    OR?: AppSettingsWhereInput[]
    NOT?: AppSettingsWhereInput | AppSettingsWhereInput[]
    brandName?: StringNullableFilter<"AppSettings"> | string | null
    brandLogoUrl?: StringNullableFilter<"AppSettings"> | string | null
    brandLogoUrlDark?: StringNullableFilter<"AppSettings"> | string | null
    brandTagline?: StringNullableFilter<"AppSettings"> | string | null
    customCss?: StringNullableFilter<"AppSettings"> | string | null
    primaryColor?: StringNullableFilter<"AppSettings"> | string | null
    accentColor?: StringNullableFilter<"AppSettings"> | string | null
    emailButtonColor?: StringNullableFilter<"AppSettings"> | string | null
    loginBgColor?: StringNullableFilter<"AppSettings"> | string | null
    loginCardColor?: StringNullableFilter<"AppSettings"> | string | null
    loginTextColor?: StringNullableFilter<"AppSettings"> | string | null
    loginInputColor?: StringNullableFilter<"AppSettings"> | string | null
    loginRingColor?: StringNullableFilter<"AppSettings"> | string | null
    loginBgColorDark?: StringNullableFilter<"AppSettings"> | string | null
    loginCardColorDark?: StringNullableFilter<"AppSettings"> | string | null
    loginTextColorDark?: StringNullableFilter<"AppSettings"> | string | null
    loginInputColorDark?: StringNullableFilter<"AppSettings"> | string | null
    loginRingColorDark?: StringNullableFilter<"AppSettings"> | string | null
    sidebarBgColor?: StringNullableFilter<"AppSettings"> | string | null
    sidebarTextColor?: StringNullableFilter<"AppSettings"> | string | null
    sidebarAccentColor?: StringNullableFilter<"AppSettings"> | string | null
    faviconUrl?: StringNullableFilter<"AppSettings"> | string | null
    loginHeading?: StringNullableFilter<"AppSettings"> | string | null
    loginSubheading?: StringNullableFilter<"AppSettings"> | string | null
    disabledPlugins?: StringNullableFilter<"AppSettings"> | string | null
    updatedAt?: DateTimeFilter<"AppSettings"> | Date | string
  }, "id">

  export type AppSettingsOrderByWithAggregationInput = {
    id?: SortOrder
    brandName?: SortOrderInput | SortOrder
    brandLogoUrl?: SortOrderInput | SortOrder
    brandLogoUrlDark?: SortOrderInput | SortOrder
    brandTagline?: SortOrderInput | SortOrder
    customCss?: SortOrderInput | SortOrder
    primaryColor?: SortOrderInput | SortOrder
    accentColor?: SortOrderInput | SortOrder
    emailButtonColor?: SortOrderInput | SortOrder
    loginBgColor?: SortOrderInput | SortOrder
    loginCardColor?: SortOrderInput | SortOrder
    loginTextColor?: SortOrderInput | SortOrder
    loginInputColor?: SortOrderInput | SortOrder
    loginRingColor?: SortOrderInput | SortOrder
    loginBgColorDark?: SortOrderInput | SortOrder
    loginCardColorDark?: SortOrderInput | SortOrder
    loginTextColorDark?: SortOrderInput | SortOrder
    loginInputColorDark?: SortOrderInput | SortOrder
    loginRingColorDark?: SortOrderInput | SortOrder
    sidebarBgColor?: SortOrderInput | SortOrder
    sidebarTextColor?: SortOrderInput | SortOrder
    sidebarAccentColor?: SortOrderInput | SortOrder
    faviconUrl?: SortOrderInput | SortOrder
    loginHeading?: SortOrderInput | SortOrder
    loginSubheading?: SortOrderInput | SortOrder
    disabledPlugins?: SortOrderInput | SortOrder
    updatedAt?: SortOrder
    _count?: AppSettingsCountOrderByAggregateInput
    _max?: AppSettingsMaxOrderByAggregateInput
    _min?: AppSettingsMinOrderByAggregateInput
  }

  export type AppSettingsScalarWhereWithAggregatesInput = {
    AND?: AppSettingsScalarWhereWithAggregatesInput | AppSettingsScalarWhereWithAggregatesInput[]
    OR?: AppSettingsScalarWhereWithAggregatesInput[]
    NOT?: AppSettingsScalarWhereWithAggregatesInput | AppSettingsScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"AppSettings"> | string
    brandName?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    brandLogoUrl?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    brandLogoUrlDark?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    brandTagline?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    customCss?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    primaryColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    accentColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    emailButtonColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginBgColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginCardColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginTextColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginInputColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginRingColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginBgColorDark?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginCardColorDark?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginTextColorDark?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginInputColorDark?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginRingColorDark?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    sidebarBgColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    sidebarTextColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    sidebarAccentColor?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    faviconUrl?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginHeading?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    loginSubheading?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    disabledPlugins?: StringNullableWithAggregatesFilter<"AppSettings"> | string | null
    updatedAt?: DateTimeWithAggregatesFilter<"AppSettings"> | Date | string
  }

  export type AuditLogWhereInput = {
    AND?: AuditLogWhereInput | AuditLogWhereInput[]
    OR?: AuditLogWhereInput[]
    NOT?: AuditLogWhereInput | AuditLogWhereInput[]
    id?: StringFilter<"AuditLog"> | string
    tenantId?: StringNullableFilter<"AuditLog"> | string | null
    userId?: StringNullableFilter<"AuditLog"> | string | null
    action?: StringFilter<"AuditLog"> | string
    entity?: StringFilter<"AuditLog"> | string
    entityId?: StringNullableFilter<"AuditLog"> | string | null
    metadata?: JsonFilter<"AuditLog">
    ipAddress?: StringNullableFilter<"AuditLog"> | string | null
    createdAt?: DateTimeFilter<"AuditLog"> | Date | string
    impersonatedBy?: StringNullableFilter<"AuditLog"> | string | null
  }

  export type AuditLogOrderByWithRelationInput = {
    id?: SortOrder
    tenantId?: SortOrderInput | SortOrder
    userId?: SortOrderInput | SortOrder
    action?: SortOrder
    entity?: SortOrder
    entityId?: SortOrderInput | SortOrder
    metadata?: SortOrder
    ipAddress?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    impersonatedBy?: SortOrderInput | SortOrder
  }

  export type AuditLogWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: AuditLogWhereInput | AuditLogWhereInput[]
    OR?: AuditLogWhereInput[]
    NOT?: AuditLogWhereInput | AuditLogWhereInput[]
    tenantId?: StringNullableFilter<"AuditLog"> | string | null
    userId?: StringNullableFilter<"AuditLog"> | string | null
    action?: StringFilter<"AuditLog"> | string
    entity?: StringFilter<"AuditLog"> | string
    entityId?: StringNullableFilter<"AuditLog"> | string | null
    metadata?: JsonFilter<"AuditLog">
    ipAddress?: StringNullableFilter<"AuditLog"> | string | null
    createdAt?: DateTimeFilter<"AuditLog"> | Date | string
    impersonatedBy?: StringNullableFilter<"AuditLog"> | string | null
  }, "id">

  export type AuditLogOrderByWithAggregationInput = {
    id?: SortOrder
    tenantId?: SortOrderInput | SortOrder
    userId?: SortOrderInput | SortOrder
    action?: SortOrder
    entity?: SortOrder
    entityId?: SortOrderInput | SortOrder
    metadata?: SortOrder
    ipAddress?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    impersonatedBy?: SortOrderInput | SortOrder
    _count?: AuditLogCountOrderByAggregateInput
    _max?: AuditLogMaxOrderByAggregateInput
    _min?: AuditLogMinOrderByAggregateInput
  }

  export type AuditLogScalarWhereWithAggregatesInput = {
    AND?: AuditLogScalarWhereWithAggregatesInput | AuditLogScalarWhereWithAggregatesInput[]
    OR?: AuditLogScalarWhereWithAggregatesInput[]
    NOT?: AuditLogScalarWhereWithAggregatesInput | AuditLogScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"AuditLog"> | string
    tenantId?: StringNullableWithAggregatesFilter<"AuditLog"> | string | null
    userId?: StringNullableWithAggregatesFilter<"AuditLog"> | string | null
    action?: StringWithAggregatesFilter<"AuditLog"> | string
    entity?: StringWithAggregatesFilter<"AuditLog"> | string
    entityId?: StringNullableWithAggregatesFilter<"AuditLog"> | string | null
    metadata?: JsonWithAggregatesFilter<"AuditLog">
    ipAddress?: StringNullableWithAggregatesFilter<"AuditLog"> | string | null
    createdAt?: DateTimeWithAggregatesFilter<"AuditLog"> | Date | string
    impersonatedBy?: StringNullableWithAggregatesFilter<"AuditLog"> | string | null
  }

  export type WaitlistEntryWhereInput = {
    AND?: WaitlistEntryWhereInput | WaitlistEntryWhereInput[]
    OR?: WaitlistEntryWhereInput[]
    NOT?: WaitlistEntryWhereInput | WaitlistEntryWhereInput[]
    id?: StringFilter<"WaitlistEntry"> | string
    email?: StringFilter<"WaitlistEntry"> | string
    name?: StringNullableFilter<"WaitlistEntry"> | string | null
    company?: StringNullableFilter<"WaitlistEntry"> | string | null
    useCase?: StringNullableFilter<"WaitlistEntry"> | string | null
    status?: EnumWaitlistStatusFilter<"WaitlistEntry"> | $Enums.WaitlistStatus
    promotedAt?: DateTimeNullableFilter<"WaitlistEntry"> | Date | string | null
    createdAt?: DateTimeFilter<"WaitlistEntry"> | Date | string
  }

  export type WaitlistEntryOrderByWithRelationInput = {
    id?: SortOrder
    email?: SortOrder
    name?: SortOrderInput | SortOrder
    company?: SortOrderInput | SortOrder
    useCase?: SortOrderInput | SortOrder
    status?: SortOrder
    promotedAt?: SortOrderInput | SortOrder
    createdAt?: SortOrder
  }

  export type WaitlistEntryWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    email?: string
    AND?: WaitlistEntryWhereInput | WaitlistEntryWhereInput[]
    OR?: WaitlistEntryWhereInput[]
    NOT?: WaitlistEntryWhereInput | WaitlistEntryWhereInput[]
    name?: StringNullableFilter<"WaitlistEntry"> | string | null
    company?: StringNullableFilter<"WaitlistEntry"> | string | null
    useCase?: StringNullableFilter<"WaitlistEntry"> | string | null
    status?: EnumWaitlistStatusFilter<"WaitlistEntry"> | $Enums.WaitlistStatus
    promotedAt?: DateTimeNullableFilter<"WaitlistEntry"> | Date | string | null
    createdAt?: DateTimeFilter<"WaitlistEntry"> | Date | string
  }, "id" | "email">

  export type WaitlistEntryOrderByWithAggregationInput = {
    id?: SortOrder
    email?: SortOrder
    name?: SortOrderInput | SortOrder
    company?: SortOrderInput | SortOrder
    useCase?: SortOrderInput | SortOrder
    status?: SortOrder
    promotedAt?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    _count?: WaitlistEntryCountOrderByAggregateInput
    _max?: WaitlistEntryMaxOrderByAggregateInput
    _min?: WaitlistEntryMinOrderByAggregateInput
  }

  export type WaitlistEntryScalarWhereWithAggregatesInput = {
    AND?: WaitlistEntryScalarWhereWithAggregatesInput | WaitlistEntryScalarWhereWithAggregatesInput[]
    OR?: WaitlistEntryScalarWhereWithAggregatesInput[]
    NOT?: WaitlistEntryScalarWhereWithAggregatesInput | WaitlistEntryScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"WaitlistEntry"> | string
    email?: StringWithAggregatesFilter<"WaitlistEntry"> | string
    name?: StringNullableWithAggregatesFilter<"WaitlistEntry"> | string | null
    company?: StringNullableWithAggregatesFilter<"WaitlistEntry"> | string | null
    useCase?: StringNullableWithAggregatesFilter<"WaitlistEntry"> | string | null
    status?: EnumWaitlistStatusWithAggregatesFilter<"WaitlistEntry"> | $Enums.WaitlistStatus
    promotedAt?: DateTimeNullableWithAggregatesFilter<"WaitlistEntry"> | Date | string | null
    createdAt?: DateTimeWithAggregatesFilter<"WaitlistEntry"> | Date | string
  }

  export type AnnotationWhereInput = {
    AND?: AnnotationWhereInput | AnnotationWhereInput[]
    OR?: AnnotationWhereInput[]
    NOT?: AnnotationWhereInput | AnnotationWhereInput[]
    id?: StringFilter<"Annotation"> | string
    jobId?: StringFilter<"Annotation"> | string
    tenantId?: StringFilter<"Annotation"> | string
    pageNum?: IntFilter<"Annotation"> | number
    authorId?: StringNullableFilter<"Annotation"> | string | null
    authorEmail?: StringFilter<"Annotation"> | string
    authorName?: StringNullableFilter<"Annotation"> | string | null
    fabricJson?: JsonFilter<"Annotation">
    createdAt?: DateTimeFilter<"Annotation"> | Date | string
    updatedAt?: DateTimeFilter<"Annotation"> | Date | string
    tenant?: XOR<TenantScalarRelationFilter, TenantWhereInput>
  }

  export type AnnotationOrderByWithRelationInput = {
    id?: SortOrder
    jobId?: SortOrder
    tenantId?: SortOrder
    pageNum?: SortOrder
    authorId?: SortOrderInput | SortOrder
    authorEmail?: SortOrder
    authorName?: SortOrderInput | SortOrder
    fabricJson?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    tenant?: TenantOrderByWithRelationInput
  }

  export type AnnotationWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: AnnotationWhereInput | AnnotationWhereInput[]
    OR?: AnnotationWhereInput[]
    NOT?: AnnotationWhereInput | AnnotationWhereInput[]
    jobId?: StringFilter<"Annotation"> | string
    tenantId?: StringFilter<"Annotation"> | string
    pageNum?: IntFilter<"Annotation"> | number
    authorId?: StringNullableFilter<"Annotation"> | string | null
    authorEmail?: StringFilter<"Annotation"> | string
    authorName?: StringNullableFilter<"Annotation"> | string | null
    fabricJson?: JsonFilter<"Annotation">
    createdAt?: DateTimeFilter<"Annotation"> | Date | string
    updatedAt?: DateTimeFilter<"Annotation"> | Date | string
    tenant?: XOR<TenantScalarRelationFilter, TenantWhereInput>
  }, "id">

  export type AnnotationOrderByWithAggregationInput = {
    id?: SortOrder
    jobId?: SortOrder
    tenantId?: SortOrder
    pageNum?: SortOrder
    authorId?: SortOrderInput | SortOrder
    authorEmail?: SortOrder
    authorName?: SortOrderInput | SortOrder
    fabricJson?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    _count?: AnnotationCountOrderByAggregateInput
    _avg?: AnnotationAvgOrderByAggregateInput
    _max?: AnnotationMaxOrderByAggregateInput
    _min?: AnnotationMinOrderByAggregateInput
    _sum?: AnnotationSumOrderByAggregateInput
  }

  export type AnnotationScalarWhereWithAggregatesInput = {
    AND?: AnnotationScalarWhereWithAggregatesInput | AnnotationScalarWhereWithAggregatesInput[]
    OR?: AnnotationScalarWhereWithAggregatesInput[]
    NOT?: AnnotationScalarWhereWithAggregatesInput | AnnotationScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Annotation"> | string
    jobId?: StringWithAggregatesFilter<"Annotation"> | string
    tenantId?: StringWithAggregatesFilter<"Annotation"> | string
    pageNum?: IntWithAggregatesFilter<"Annotation"> | number
    authorId?: StringNullableWithAggregatesFilter<"Annotation"> | string | null
    authorEmail?: StringWithAggregatesFilter<"Annotation"> | string
    authorName?: StringNullableWithAggregatesFilter<"Annotation"> | string | null
    fabricJson?: JsonWithAggregatesFilter<"Annotation">
    createdAt?: DateTimeWithAggregatesFilter<"Annotation"> | Date | string
    updatedAt?: DateTimeWithAggregatesFilter<"Annotation"> | Date | string
  }

  export type ReportViewWhereInput = {
    AND?: ReportViewWhereInput | ReportViewWhereInput[]
    OR?: ReportViewWhereInput[]
    NOT?: ReportViewWhereInput | ReportViewWhereInput[]
    id?: StringFilter<"ReportView"> | string
    jobId?: StringFilter<"ReportView"> | string
    tenantId?: StringFilter<"ReportView"> | string
    reportToken?: StringFilter<"ReportView"> | string
    viewerEmail?: StringNullableFilter<"ReportView"> | string | null
    viewerName?: StringNullableFilter<"ReportView"> | string | null
    ipAddress?: StringNullableFilter<"ReportView"> | string | null
    userAgent?: StringNullableFilter<"ReportView"> | string | null
    viewedAt?: DateTimeFilter<"ReportView"> | Date | string
    tenant?: XOR<TenantScalarRelationFilter, TenantWhereInput>
  }

  export type ReportViewOrderByWithRelationInput = {
    id?: SortOrder
    jobId?: SortOrder
    tenantId?: SortOrder
    reportToken?: SortOrder
    viewerEmail?: SortOrderInput | SortOrder
    viewerName?: SortOrderInput | SortOrder
    ipAddress?: SortOrderInput | SortOrder
    userAgent?: SortOrderInput | SortOrder
    viewedAt?: SortOrder
    tenant?: TenantOrderByWithRelationInput
  }

  export type ReportViewWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: ReportViewWhereInput | ReportViewWhereInput[]
    OR?: ReportViewWhereInput[]
    NOT?: ReportViewWhereInput | ReportViewWhereInput[]
    jobId?: StringFilter<"ReportView"> | string
    tenantId?: StringFilter<"ReportView"> | string
    reportToken?: StringFilter<"ReportView"> | string
    viewerEmail?: StringNullableFilter<"ReportView"> | string | null
    viewerName?: StringNullableFilter<"ReportView"> | string | null
    ipAddress?: StringNullableFilter<"ReportView"> | string | null
    userAgent?: StringNullableFilter<"ReportView"> | string | null
    viewedAt?: DateTimeFilter<"ReportView"> | Date | string
    tenant?: XOR<TenantScalarRelationFilter, TenantWhereInput>
  }, "id">

  export type ReportViewOrderByWithAggregationInput = {
    id?: SortOrder
    jobId?: SortOrder
    tenantId?: SortOrder
    reportToken?: SortOrder
    viewerEmail?: SortOrderInput | SortOrder
    viewerName?: SortOrderInput | SortOrder
    ipAddress?: SortOrderInput | SortOrder
    userAgent?: SortOrderInput | SortOrder
    viewedAt?: SortOrder
    _count?: ReportViewCountOrderByAggregateInput
    _max?: ReportViewMaxOrderByAggregateInput
    _min?: ReportViewMinOrderByAggregateInput
  }

  export type ReportViewScalarWhereWithAggregatesInput = {
    AND?: ReportViewScalarWhereWithAggregatesInput | ReportViewScalarWhereWithAggregatesInput[]
    OR?: ReportViewScalarWhereWithAggregatesInput[]
    NOT?: ReportViewScalarWhereWithAggregatesInput | ReportViewScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"ReportView"> | string
    jobId?: StringWithAggregatesFilter<"ReportView"> | string
    tenantId?: StringWithAggregatesFilter<"ReportView"> | string
    reportToken?: StringWithAggregatesFilter<"ReportView"> | string
    viewerEmail?: StringNullableWithAggregatesFilter<"ReportView"> | string | null
    viewerName?: StringNullableWithAggregatesFilter<"ReportView"> | string | null
    ipAddress?: StringNullableWithAggregatesFilter<"ReportView"> | string | null
    userAgent?: StringNullableWithAggregatesFilter<"ReportView"> | string | null
    viewedAt?: DateTimeWithAggregatesFilter<"ReportView"> | Date | string
  }

  export type TenantCreateInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
    users?: TenantUserCreateNestedManyWithoutTenantInput
    invites?: TenantInviteCreateNestedManyWithoutTenantInput
    annotations?: AnnotationCreateNestedManyWithoutTenantInput
    reportViews?: ReportViewCreateNestedManyWithoutTenantInput
  }

  export type TenantUncheckedCreateInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
    users?: TenantUserUncheckedCreateNestedManyWithoutTenantInput
    invites?: TenantInviteUncheckedCreateNestedManyWithoutTenantInput
    annotations?: AnnotationUncheckedCreateNestedManyWithoutTenantInput
    reportViews?: ReportViewUncheckedCreateNestedManyWithoutTenantInput
  }

  export type TenantUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    users?: TenantUserUpdateManyWithoutTenantNestedInput
    invites?: TenantInviteUpdateManyWithoutTenantNestedInput
    annotations?: AnnotationUpdateManyWithoutTenantNestedInput
    reportViews?: ReportViewUpdateManyWithoutTenantNestedInput
  }

  export type TenantUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    users?: TenantUserUncheckedUpdateManyWithoutTenantNestedInput
    invites?: TenantInviteUncheckedUpdateManyWithoutTenantNestedInput
    annotations?: AnnotationUncheckedUpdateManyWithoutTenantNestedInput
    reportViews?: ReportViewUncheckedUpdateManyWithoutTenantNestedInput
  }

  export type TenantCreateManyInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type TenantUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type UserCreateInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
    tenants?: TenantUserCreateNestedManyWithoutUserInput
    sessions?: SessionCreateNestedManyWithoutUserInput
    magicLinks?: MagicLinkCreateNestedManyWithoutUserInput
    invites?: TenantInviteCreateNestedManyWithoutUserInput
  }

  export type UserUncheckedCreateInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
    tenants?: TenantUserUncheckedCreateNestedManyWithoutUserInput
    sessions?: SessionUncheckedCreateNestedManyWithoutUserInput
    magicLinks?: MagicLinkUncheckedCreateNestedManyWithoutUserInput
    invites?: TenantInviteUncheckedCreateNestedManyWithoutUserInput
  }

  export type UserUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenants?: TenantUserUpdateManyWithoutUserNestedInput
    sessions?: SessionUpdateManyWithoutUserNestedInput
    magicLinks?: MagicLinkUpdateManyWithoutUserNestedInput
    invites?: TenantInviteUpdateManyWithoutUserNestedInput
  }

  export type UserUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenants?: TenantUserUncheckedUpdateManyWithoutUserNestedInput
    sessions?: SessionUncheckedUpdateManyWithoutUserNestedInput
    magicLinks?: MagicLinkUncheckedUpdateManyWithoutUserNestedInput
    invites?: TenantInviteUncheckedUpdateManyWithoutUserNestedInput
  }

  export type UserCreateManyInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type UserUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type UserUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantUserCreateInput = {
    id?: string
    role?: $Enums.TenantRole
    joinedAt?: Date | string
    user: UserCreateNestedOneWithoutTenantsInput
    tenant: TenantCreateNestedOneWithoutUsersInput
  }

  export type TenantUserUncheckedCreateInput = {
    id?: string
    userId: string
    tenantId: string
    role?: $Enums.TenantRole
    joinedAt?: Date | string
  }

  export type TenantUserUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    joinedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    user?: UserUpdateOneRequiredWithoutTenantsNestedInput
    tenant?: TenantUpdateOneRequiredWithoutUsersNestedInput
  }

  export type TenantUserUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    joinedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantUserCreateManyInput = {
    id?: string
    userId: string
    tenantId: string
    role?: $Enums.TenantRole
    joinedAt?: Date | string
  }

  export type TenantUserUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    joinedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantUserUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    joinedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantInviteCreateInput = {
    id?: string
    role?: $Enums.TenantRole
    token: string
    expiresAt: Date | string
    usedAt?: Date | string | null
    acceptedAt?: Date | string | null
    revokedAt?: Date | string | null
    createdAt?: Date | string
    tenant: TenantCreateNestedOneWithoutInvitesInput
    user: UserCreateNestedOneWithoutInvitesInput
  }

  export type TenantInviteUncheckedCreateInput = {
    id?: string
    tenantId: string
    email: string
    role?: $Enums.TenantRole
    token: string
    expiresAt: Date | string
    usedAt?: Date | string | null
    acceptedAt?: Date | string | null
    revokedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type TenantInviteUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    acceptedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    revokedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenant?: TenantUpdateOneRequiredWithoutInvitesNestedInput
    user?: UserUpdateOneRequiredWithoutInvitesNestedInput
  }

  export type TenantInviteUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    acceptedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    revokedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantInviteCreateManyInput = {
    id?: string
    tenantId: string
    email: string
    role?: $Enums.TenantRole
    token: string
    expiresAt: Date | string
    usedAt?: Date | string | null
    acceptedAt?: Date | string | null
    revokedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type TenantInviteUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    acceptedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    revokedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantInviteUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    acceptedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    revokedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type SessionCreateInput = {
    id?: string
    token: string
    expiresAt: Date | string
    createdAt?: Date | string
    ipAddress?: string | null
    userAgent?: string | null
    impersonatingTenantId?: string | null
    user: UserCreateNestedOneWithoutSessionsInput
  }

  export type SessionUncheckedCreateInput = {
    id?: string
    userId: string
    token: string
    expiresAt: Date | string
    createdAt?: Date | string
    ipAddress?: string | null
    userAgent?: string | null
    impersonatingTenantId?: string | null
  }

  export type SessionUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    impersonatingTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    user?: UserUpdateOneRequiredWithoutSessionsNestedInput
  }

  export type SessionUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    impersonatingTenantId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type SessionCreateManyInput = {
    id?: string
    userId: string
    token: string
    expiresAt: Date | string
    createdAt?: Date | string
    ipAddress?: string | null
    userAgent?: string | null
    impersonatingTenantId?: string | null
  }

  export type SessionUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    impersonatingTenantId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type SessionUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    impersonatingTenantId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type MagicLinkCreateInput = {
    id?: string
    token: string
    pollingToken?: string | null
    code?: string | null
    ipAddress?: string | null
    expiresAt: Date | string
    usedAt?: Date | string | null
    createdAt?: Date | string
    user: UserCreateNestedOneWithoutMagicLinksInput
  }

  export type MagicLinkUncheckedCreateInput = {
    id?: string
    userId: string
    token: string
    pollingToken?: string | null
    code?: string | null
    ipAddress?: string | null
    expiresAt: Date | string
    usedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type MagicLinkUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    pollingToken?: NullableStringFieldUpdateOperationsInput | string | null
    code?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    user?: UserUpdateOneRequiredWithoutMagicLinksNestedInput
  }

  export type MagicLinkUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    pollingToken?: NullableStringFieldUpdateOperationsInput | string | null
    code?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type MagicLinkCreateManyInput = {
    id?: string
    userId: string
    token: string
    pollingToken?: string | null
    code?: string | null
    ipAddress?: string | null
    expiresAt: Date | string
    usedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type MagicLinkUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    pollingToken?: NullableStringFieldUpdateOperationsInput | string | null
    code?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type MagicLinkUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    pollingToken?: NullableStringFieldUpdateOperationsInput | string | null
    code?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AppSettingsCreateInput = {
    id?: string
    brandName?: string | null
    brandLogoUrl?: string | null
    brandLogoUrlDark?: string | null
    brandTagline?: string | null
    customCss?: string | null
    primaryColor?: string | null
    accentColor?: string | null
    emailButtonColor?: string | null
    loginBgColor?: string | null
    loginCardColor?: string | null
    loginTextColor?: string | null
    loginInputColor?: string | null
    loginRingColor?: string | null
    loginBgColorDark?: string | null
    loginCardColorDark?: string | null
    loginTextColorDark?: string | null
    loginInputColorDark?: string | null
    loginRingColorDark?: string | null
    sidebarBgColor?: string | null
    sidebarTextColor?: string | null
    sidebarAccentColor?: string | null
    faviconUrl?: string | null
    loginHeading?: string | null
    loginSubheading?: string | null
    disabledPlugins?: string | null
    updatedAt?: Date | string
  }

  export type AppSettingsUncheckedCreateInput = {
    id?: string
    brandName?: string | null
    brandLogoUrl?: string | null
    brandLogoUrlDark?: string | null
    brandTagline?: string | null
    customCss?: string | null
    primaryColor?: string | null
    accentColor?: string | null
    emailButtonColor?: string | null
    loginBgColor?: string | null
    loginCardColor?: string | null
    loginTextColor?: string | null
    loginInputColor?: string | null
    loginRingColor?: string | null
    loginBgColorDark?: string | null
    loginCardColorDark?: string | null
    loginTextColorDark?: string | null
    loginInputColorDark?: string | null
    loginRingColorDark?: string | null
    sidebarBgColor?: string | null
    sidebarTextColor?: string | null
    sidebarAccentColor?: string | null
    faviconUrl?: string | null
    loginHeading?: string | null
    loginSubheading?: string | null
    disabledPlugins?: string | null
    updatedAt?: Date | string
  }

  export type AppSettingsUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    brandName?: NullableStringFieldUpdateOperationsInput | string | null
    brandLogoUrl?: NullableStringFieldUpdateOperationsInput | string | null
    brandLogoUrlDark?: NullableStringFieldUpdateOperationsInput | string | null
    brandTagline?: NullableStringFieldUpdateOperationsInput | string | null
    customCss?: NullableStringFieldUpdateOperationsInput | string | null
    primaryColor?: NullableStringFieldUpdateOperationsInput | string | null
    accentColor?: NullableStringFieldUpdateOperationsInput | string | null
    emailButtonColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginBgColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginCardColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginTextColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginInputColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginRingColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginBgColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginCardColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginTextColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginInputColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginRingColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarBgColor?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarTextColor?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarAccentColor?: NullableStringFieldUpdateOperationsInput | string | null
    faviconUrl?: NullableStringFieldUpdateOperationsInput | string | null
    loginHeading?: NullableStringFieldUpdateOperationsInput | string | null
    loginSubheading?: NullableStringFieldUpdateOperationsInput | string | null
    disabledPlugins?: NullableStringFieldUpdateOperationsInput | string | null
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AppSettingsUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    brandName?: NullableStringFieldUpdateOperationsInput | string | null
    brandLogoUrl?: NullableStringFieldUpdateOperationsInput | string | null
    brandLogoUrlDark?: NullableStringFieldUpdateOperationsInput | string | null
    brandTagline?: NullableStringFieldUpdateOperationsInput | string | null
    customCss?: NullableStringFieldUpdateOperationsInput | string | null
    primaryColor?: NullableStringFieldUpdateOperationsInput | string | null
    accentColor?: NullableStringFieldUpdateOperationsInput | string | null
    emailButtonColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginBgColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginCardColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginTextColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginInputColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginRingColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginBgColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginCardColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginTextColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginInputColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginRingColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarBgColor?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarTextColor?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarAccentColor?: NullableStringFieldUpdateOperationsInput | string | null
    faviconUrl?: NullableStringFieldUpdateOperationsInput | string | null
    loginHeading?: NullableStringFieldUpdateOperationsInput | string | null
    loginSubheading?: NullableStringFieldUpdateOperationsInput | string | null
    disabledPlugins?: NullableStringFieldUpdateOperationsInput | string | null
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AppSettingsCreateManyInput = {
    id?: string
    brandName?: string | null
    brandLogoUrl?: string | null
    brandLogoUrlDark?: string | null
    brandTagline?: string | null
    customCss?: string | null
    primaryColor?: string | null
    accentColor?: string | null
    emailButtonColor?: string | null
    loginBgColor?: string | null
    loginCardColor?: string | null
    loginTextColor?: string | null
    loginInputColor?: string | null
    loginRingColor?: string | null
    loginBgColorDark?: string | null
    loginCardColorDark?: string | null
    loginTextColorDark?: string | null
    loginInputColorDark?: string | null
    loginRingColorDark?: string | null
    sidebarBgColor?: string | null
    sidebarTextColor?: string | null
    sidebarAccentColor?: string | null
    faviconUrl?: string | null
    loginHeading?: string | null
    loginSubheading?: string | null
    disabledPlugins?: string | null
    updatedAt?: Date | string
  }

  export type AppSettingsUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    brandName?: NullableStringFieldUpdateOperationsInput | string | null
    brandLogoUrl?: NullableStringFieldUpdateOperationsInput | string | null
    brandLogoUrlDark?: NullableStringFieldUpdateOperationsInput | string | null
    brandTagline?: NullableStringFieldUpdateOperationsInput | string | null
    customCss?: NullableStringFieldUpdateOperationsInput | string | null
    primaryColor?: NullableStringFieldUpdateOperationsInput | string | null
    accentColor?: NullableStringFieldUpdateOperationsInput | string | null
    emailButtonColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginBgColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginCardColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginTextColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginInputColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginRingColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginBgColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginCardColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginTextColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginInputColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginRingColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarBgColor?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarTextColor?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarAccentColor?: NullableStringFieldUpdateOperationsInput | string | null
    faviconUrl?: NullableStringFieldUpdateOperationsInput | string | null
    loginHeading?: NullableStringFieldUpdateOperationsInput | string | null
    loginSubheading?: NullableStringFieldUpdateOperationsInput | string | null
    disabledPlugins?: NullableStringFieldUpdateOperationsInput | string | null
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AppSettingsUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    brandName?: NullableStringFieldUpdateOperationsInput | string | null
    brandLogoUrl?: NullableStringFieldUpdateOperationsInput | string | null
    brandLogoUrlDark?: NullableStringFieldUpdateOperationsInput | string | null
    brandTagline?: NullableStringFieldUpdateOperationsInput | string | null
    customCss?: NullableStringFieldUpdateOperationsInput | string | null
    primaryColor?: NullableStringFieldUpdateOperationsInput | string | null
    accentColor?: NullableStringFieldUpdateOperationsInput | string | null
    emailButtonColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginBgColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginCardColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginTextColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginInputColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginRingColor?: NullableStringFieldUpdateOperationsInput | string | null
    loginBgColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginCardColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginTextColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginInputColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    loginRingColorDark?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarBgColor?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarTextColor?: NullableStringFieldUpdateOperationsInput | string | null
    sidebarAccentColor?: NullableStringFieldUpdateOperationsInput | string | null
    faviconUrl?: NullableStringFieldUpdateOperationsInput | string | null
    loginHeading?: NullableStringFieldUpdateOperationsInput | string | null
    loginSubheading?: NullableStringFieldUpdateOperationsInput | string | null
    disabledPlugins?: NullableStringFieldUpdateOperationsInput | string | null
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AuditLogCreateInput = {
    id?: string
    tenantId?: string | null
    userId?: string | null
    action: string
    entity: string
    entityId?: string | null
    metadata?: JsonNullValueInput | InputJsonValue
    ipAddress?: string | null
    createdAt?: Date | string
    impersonatedBy?: string | null
  }

  export type AuditLogUncheckedCreateInput = {
    id?: string
    tenantId?: string | null
    userId?: string | null
    action: string
    entity: string
    entityId?: string | null
    metadata?: JsonNullValueInput | InputJsonValue
    ipAddress?: string | null
    createdAt?: Date | string
    impersonatedBy?: string | null
  }

  export type AuditLogUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    tenantId?: NullableStringFieldUpdateOperationsInput | string | null
    userId?: NullableStringFieldUpdateOperationsInput | string | null
    action?: StringFieldUpdateOperationsInput | string
    entity?: StringFieldUpdateOperationsInput | string
    entityId?: NullableStringFieldUpdateOperationsInput | string | null
    metadata?: JsonNullValueInput | InputJsonValue
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    impersonatedBy?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type AuditLogUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    tenantId?: NullableStringFieldUpdateOperationsInput | string | null
    userId?: NullableStringFieldUpdateOperationsInput | string | null
    action?: StringFieldUpdateOperationsInput | string
    entity?: StringFieldUpdateOperationsInput | string
    entityId?: NullableStringFieldUpdateOperationsInput | string | null
    metadata?: JsonNullValueInput | InputJsonValue
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    impersonatedBy?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type AuditLogCreateManyInput = {
    id?: string
    tenantId?: string | null
    userId?: string | null
    action: string
    entity: string
    entityId?: string | null
    metadata?: JsonNullValueInput | InputJsonValue
    ipAddress?: string | null
    createdAt?: Date | string
    impersonatedBy?: string | null
  }

  export type AuditLogUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    tenantId?: NullableStringFieldUpdateOperationsInput | string | null
    userId?: NullableStringFieldUpdateOperationsInput | string | null
    action?: StringFieldUpdateOperationsInput | string
    entity?: StringFieldUpdateOperationsInput | string
    entityId?: NullableStringFieldUpdateOperationsInput | string | null
    metadata?: JsonNullValueInput | InputJsonValue
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    impersonatedBy?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type AuditLogUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    tenantId?: NullableStringFieldUpdateOperationsInput | string | null
    userId?: NullableStringFieldUpdateOperationsInput | string | null
    action?: StringFieldUpdateOperationsInput | string
    entity?: StringFieldUpdateOperationsInput | string
    entityId?: NullableStringFieldUpdateOperationsInput | string | null
    metadata?: JsonNullValueInput | InputJsonValue
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    impersonatedBy?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type WaitlistEntryCreateInput = {
    id?: string
    email: string
    name?: string | null
    company?: string | null
    useCase?: string | null
    status?: $Enums.WaitlistStatus
    promotedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type WaitlistEntryUncheckedCreateInput = {
    id?: string
    email: string
    name?: string | null
    company?: string | null
    useCase?: string | null
    status?: $Enums.WaitlistStatus
    promotedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type WaitlistEntryUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    company?: NullableStringFieldUpdateOperationsInput | string | null
    useCase?: NullableStringFieldUpdateOperationsInput | string | null
    status?: EnumWaitlistStatusFieldUpdateOperationsInput | $Enums.WaitlistStatus
    promotedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type WaitlistEntryUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    company?: NullableStringFieldUpdateOperationsInput | string | null
    useCase?: NullableStringFieldUpdateOperationsInput | string | null
    status?: EnumWaitlistStatusFieldUpdateOperationsInput | $Enums.WaitlistStatus
    promotedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type WaitlistEntryCreateManyInput = {
    id?: string
    email: string
    name?: string | null
    company?: string | null
    useCase?: string | null
    status?: $Enums.WaitlistStatus
    promotedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type WaitlistEntryUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    company?: NullableStringFieldUpdateOperationsInput | string | null
    useCase?: NullableStringFieldUpdateOperationsInput | string | null
    status?: EnumWaitlistStatusFieldUpdateOperationsInput | $Enums.WaitlistStatus
    promotedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type WaitlistEntryUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    company?: NullableStringFieldUpdateOperationsInput | string | null
    useCase?: NullableStringFieldUpdateOperationsInput | string | null
    status?: EnumWaitlistStatusFieldUpdateOperationsInput | $Enums.WaitlistStatus
    promotedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AnnotationCreateInput = {
    id?: string
    jobId: string
    pageNum: number
    authorId?: string | null
    authorEmail: string
    authorName?: string | null
    fabricJson: JsonNullValueInput | InputJsonValue
    createdAt?: Date | string
    updatedAt?: Date | string
    tenant: TenantCreateNestedOneWithoutAnnotationsInput
  }

  export type AnnotationUncheckedCreateInput = {
    id?: string
    jobId: string
    tenantId: string
    pageNum: number
    authorId?: string | null
    authorEmail: string
    authorName?: string | null
    fabricJson: JsonNullValueInput | InputJsonValue
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type AnnotationUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    pageNum?: IntFieldUpdateOperationsInput | number
    authorId?: NullableStringFieldUpdateOperationsInput | string | null
    authorEmail?: StringFieldUpdateOperationsInput | string
    authorName?: NullableStringFieldUpdateOperationsInput | string | null
    fabricJson?: JsonNullValueInput | InputJsonValue
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenant?: TenantUpdateOneRequiredWithoutAnnotationsNestedInput
  }

  export type AnnotationUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    pageNum?: IntFieldUpdateOperationsInput | number
    authorId?: NullableStringFieldUpdateOperationsInput | string | null
    authorEmail?: StringFieldUpdateOperationsInput | string
    authorName?: NullableStringFieldUpdateOperationsInput | string | null
    fabricJson?: JsonNullValueInput | InputJsonValue
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AnnotationCreateManyInput = {
    id?: string
    jobId: string
    tenantId: string
    pageNum: number
    authorId?: string | null
    authorEmail: string
    authorName?: string | null
    fabricJson: JsonNullValueInput | InputJsonValue
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type AnnotationUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    pageNum?: IntFieldUpdateOperationsInput | number
    authorId?: NullableStringFieldUpdateOperationsInput | string | null
    authorEmail?: StringFieldUpdateOperationsInput | string
    authorName?: NullableStringFieldUpdateOperationsInput | string | null
    fabricJson?: JsonNullValueInput | InputJsonValue
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AnnotationUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    pageNum?: IntFieldUpdateOperationsInput | number
    authorId?: NullableStringFieldUpdateOperationsInput | string | null
    authorEmail?: StringFieldUpdateOperationsInput | string
    authorName?: NullableStringFieldUpdateOperationsInput | string | null
    fabricJson?: JsonNullValueInput | InputJsonValue
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type ReportViewCreateInput = {
    id?: string
    jobId: string
    reportToken: string
    viewerEmail?: string | null
    viewerName?: string | null
    ipAddress?: string | null
    userAgent?: string | null
    viewedAt?: Date | string
    tenant: TenantCreateNestedOneWithoutReportViewsInput
  }

  export type ReportViewUncheckedCreateInput = {
    id?: string
    jobId: string
    tenantId: string
    reportToken: string
    viewerEmail?: string | null
    viewerName?: string | null
    ipAddress?: string | null
    userAgent?: string | null
    viewedAt?: Date | string
  }

  export type ReportViewUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    reportToken?: StringFieldUpdateOperationsInput | string
    viewerEmail?: NullableStringFieldUpdateOperationsInput | string | null
    viewerName?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    viewedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenant?: TenantUpdateOneRequiredWithoutReportViewsNestedInput
  }

  export type ReportViewUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    reportToken?: StringFieldUpdateOperationsInput | string
    viewerEmail?: NullableStringFieldUpdateOperationsInput | string | null
    viewerName?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    viewedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type ReportViewCreateManyInput = {
    id?: string
    jobId: string
    tenantId: string
    reportToken: string
    viewerEmail?: string | null
    viewerName?: string | null
    ipAddress?: string | null
    userAgent?: string | null
    viewedAt?: Date | string
  }

  export type ReportViewUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    reportToken?: StringFieldUpdateOperationsInput | string
    viewerEmail?: NullableStringFieldUpdateOperationsInput | string | null
    viewerName?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    viewedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type ReportViewUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    reportToken?: StringFieldUpdateOperationsInput | string
    viewerEmail?: NullableStringFieldUpdateOperationsInput | string | null
    viewerName?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    viewedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type StringFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringFilter<$PrismaModel> | string
  }

  export type StringNullableFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringNullableFilter<$PrismaModel> | string | null
  }
  export type JsonFilter<$PrismaModel = never> =
    | PatchUndefined<
        Either<Required<JsonFilterBase<$PrismaModel>>, Exclude<keyof Required<JsonFilterBase<$PrismaModel>>, 'path'>>,
        Required<JsonFilterBase<$PrismaModel>>
      >
    | OptionalFlat<Omit<Required<JsonFilterBase<$PrismaModel>>, 'path'>>

  export type JsonFilterBase<$PrismaModel = never> = {
    equals?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
    path?: string[]
    mode?: QueryMode | EnumQueryModeFieldRefInput<$PrismaModel>
    string_contains?: string | StringFieldRefInput<$PrismaModel>
    string_starts_with?: string | StringFieldRefInput<$PrismaModel>
    string_ends_with?: string | StringFieldRefInput<$PrismaModel>
    array_starts_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_ends_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_contains?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    lt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    lte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    not?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
  }

  export type EnumTenantStatusFilter<$PrismaModel = never> = {
    equals?: $Enums.TenantStatus | EnumTenantStatusFieldRefInput<$PrismaModel>
    in?: $Enums.TenantStatus[] | ListEnumTenantStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.TenantStatus[] | ListEnumTenantStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumTenantStatusFilter<$PrismaModel> | $Enums.TenantStatus
  }

  export type DateTimeFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeFilter<$PrismaModel> | Date | string
  }

  export type TenantUserListRelationFilter = {
    every?: TenantUserWhereInput
    some?: TenantUserWhereInput
    none?: TenantUserWhereInput
  }

  export type TenantInviteListRelationFilter = {
    every?: TenantInviteWhereInput
    some?: TenantInviteWhereInput
    none?: TenantInviteWhereInput
  }

  export type AnnotationListRelationFilter = {
    every?: AnnotationWhereInput
    some?: AnnotationWhereInput
    none?: AnnotationWhereInput
  }

  export type ReportViewListRelationFilter = {
    every?: ReportViewWhereInput
    some?: ReportViewWhereInput
    none?: ReportViewWhereInput
  }

  export type SortOrderInput = {
    sort: SortOrder
    nulls?: NullsOrder
  }

  export type TenantUserOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type TenantInviteOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type AnnotationOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type ReportViewOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type TenantCountOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    slug?: SortOrder
    domain?: SortOrder
    engineTenantId?: SortOrder
    settings?: SortOrder
    status?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type TenantMaxOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    slug?: SortOrder
    domain?: SortOrder
    engineTenantId?: SortOrder
    status?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type TenantMinOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    slug?: SortOrder
    domain?: SortOrder
    engineTenantId?: SortOrder
    status?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type StringWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringWithAggregatesFilter<$PrismaModel> | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedStringFilter<$PrismaModel>
    _max?: NestedStringFilter<$PrismaModel>
  }

  export type StringNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringNullableWithAggregatesFilter<$PrismaModel> | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedStringNullableFilter<$PrismaModel>
    _max?: NestedStringNullableFilter<$PrismaModel>
  }
  export type JsonWithAggregatesFilter<$PrismaModel = never> =
    | PatchUndefined<
        Either<Required<JsonWithAggregatesFilterBase<$PrismaModel>>, Exclude<keyof Required<JsonWithAggregatesFilterBase<$PrismaModel>>, 'path'>>,
        Required<JsonWithAggregatesFilterBase<$PrismaModel>>
      >
    | OptionalFlat<Omit<Required<JsonWithAggregatesFilterBase<$PrismaModel>>, 'path'>>

  export type JsonWithAggregatesFilterBase<$PrismaModel = never> = {
    equals?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
    path?: string[]
    mode?: QueryMode | EnumQueryModeFieldRefInput<$PrismaModel>
    string_contains?: string | StringFieldRefInput<$PrismaModel>
    string_starts_with?: string | StringFieldRefInput<$PrismaModel>
    string_ends_with?: string | StringFieldRefInput<$PrismaModel>
    array_starts_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_ends_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_contains?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    lt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    lte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    not?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedJsonFilter<$PrismaModel>
    _max?: NestedJsonFilter<$PrismaModel>
  }

  export type EnumTenantStatusWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.TenantStatus | EnumTenantStatusFieldRefInput<$PrismaModel>
    in?: $Enums.TenantStatus[] | ListEnumTenantStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.TenantStatus[] | ListEnumTenantStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumTenantStatusWithAggregatesFilter<$PrismaModel> | $Enums.TenantStatus
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumTenantStatusFilter<$PrismaModel>
    _max?: NestedEnumTenantStatusFilter<$PrismaModel>
  }

  export type DateTimeWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeWithAggregatesFilter<$PrismaModel> | Date | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedDateTimeFilter<$PrismaModel>
    _max?: NestedDateTimeFilter<$PrismaModel>
  }

  export type BoolFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolFilter<$PrismaModel> | boolean
  }

  export type SessionListRelationFilter = {
    every?: SessionWhereInput
    some?: SessionWhereInput
    none?: SessionWhereInput
  }

  export type MagicLinkListRelationFilter = {
    every?: MagicLinkWhereInput
    some?: MagicLinkWhereInput
    none?: MagicLinkWhereInput
  }

  export type SessionOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type MagicLinkOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type UserCountOrderByAggregateInput = {
    id?: SortOrder
    email?: SortOrder
    name?: SortOrder
    avatarUrl?: SortOrder
    isSuperAdmin?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type UserMaxOrderByAggregateInput = {
    id?: SortOrder
    email?: SortOrder
    name?: SortOrder
    avatarUrl?: SortOrder
    isSuperAdmin?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type UserMinOrderByAggregateInput = {
    id?: SortOrder
    email?: SortOrder
    name?: SortOrder
    avatarUrl?: SortOrder
    isSuperAdmin?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type BoolWithAggregatesFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolWithAggregatesFilter<$PrismaModel> | boolean
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedBoolFilter<$PrismaModel>
    _max?: NestedBoolFilter<$PrismaModel>
  }

  export type EnumTenantRoleFilter<$PrismaModel = never> = {
    equals?: $Enums.TenantRole | EnumTenantRoleFieldRefInput<$PrismaModel>
    in?: $Enums.TenantRole[] | ListEnumTenantRoleFieldRefInput<$PrismaModel>
    notIn?: $Enums.TenantRole[] | ListEnumTenantRoleFieldRefInput<$PrismaModel>
    not?: NestedEnumTenantRoleFilter<$PrismaModel> | $Enums.TenantRole
  }

  export type UserScalarRelationFilter = {
    is?: UserWhereInput
    isNot?: UserWhereInput
  }

  export type TenantScalarRelationFilter = {
    is?: TenantWhereInput
    isNot?: TenantWhereInput
  }

  export type TenantUserUserIdTenantIdCompoundUniqueInput = {
    userId: string
    tenantId: string
  }

  export type TenantUserCountOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    tenantId?: SortOrder
    role?: SortOrder
    joinedAt?: SortOrder
  }

  export type TenantUserMaxOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    tenantId?: SortOrder
    role?: SortOrder
    joinedAt?: SortOrder
  }

  export type TenantUserMinOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    tenantId?: SortOrder
    role?: SortOrder
    joinedAt?: SortOrder
  }

  export type EnumTenantRoleWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.TenantRole | EnumTenantRoleFieldRefInput<$PrismaModel>
    in?: $Enums.TenantRole[] | ListEnumTenantRoleFieldRefInput<$PrismaModel>
    notIn?: $Enums.TenantRole[] | ListEnumTenantRoleFieldRefInput<$PrismaModel>
    not?: NestedEnumTenantRoleWithAggregatesFilter<$PrismaModel> | $Enums.TenantRole
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumTenantRoleFilter<$PrismaModel>
    _max?: NestedEnumTenantRoleFilter<$PrismaModel>
  }

  export type DateTimeNullableFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableFilter<$PrismaModel> | Date | string | null
  }

  export type TenantInviteTenantIdEmailCompoundUniqueInput = {
    tenantId: string
    email: string
  }

  export type TenantInviteCountOrderByAggregateInput = {
    id?: SortOrder
    tenantId?: SortOrder
    email?: SortOrder
    role?: SortOrder
    token?: SortOrder
    expiresAt?: SortOrder
    usedAt?: SortOrder
    acceptedAt?: SortOrder
    revokedAt?: SortOrder
    createdAt?: SortOrder
  }

  export type TenantInviteMaxOrderByAggregateInput = {
    id?: SortOrder
    tenantId?: SortOrder
    email?: SortOrder
    role?: SortOrder
    token?: SortOrder
    expiresAt?: SortOrder
    usedAt?: SortOrder
    acceptedAt?: SortOrder
    revokedAt?: SortOrder
    createdAt?: SortOrder
  }

  export type TenantInviteMinOrderByAggregateInput = {
    id?: SortOrder
    tenantId?: SortOrder
    email?: SortOrder
    role?: SortOrder
    token?: SortOrder
    expiresAt?: SortOrder
    usedAt?: SortOrder
    acceptedAt?: SortOrder
    revokedAt?: SortOrder
    createdAt?: SortOrder
  }

  export type DateTimeNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableWithAggregatesFilter<$PrismaModel> | Date | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedDateTimeNullableFilter<$PrismaModel>
    _max?: NestedDateTimeNullableFilter<$PrismaModel>
  }

  export type SessionCountOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    token?: SortOrder
    expiresAt?: SortOrder
    createdAt?: SortOrder
    ipAddress?: SortOrder
    userAgent?: SortOrder
    impersonatingTenantId?: SortOrder
  }

  export type SessionMaxOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    token?: SortOrder
    expiresAt?: SortOrder
    createdAt?: SortOrder
    ipAddress?: SortOrder
    userAgent?: SortOrder
    impersonatingTenantId?: SortOrder
  }

  export type SessionMinOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    token?: SortOrder
    expiresAt?: SortOrder
    createdAt?: SortOrder
    ipAddress?: SortOrder
    userAgent?: SortOrder
    impersonatingTenantId?: SortOrder
  }

  export type MagicLinkCountOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    token?: SortOrder
    pollingToken?: SortOrder
    code?: SortOrder
    ipAddress?: SortOrder
    expiresAt?: SortOrder
    usedAt?: SortOrder
    createdAt?: SortOrder
  }

  export type MagicLinkMaxOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    token?: SortOrder
    pollingToken?: SortOrder
    code?: SortOrder
    ipAddress?: SortOrder
    expiresAt?: SortOrder
    usedAt?: SortOrder
    createdAt?: SortOrder
  }

  export type MagicLinkMinOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    token?: SortOrder
    pollingToken?: SortOrder
    code?: SortOrder
    ipAddress?: SortOrder
    expiresAt?: SortOrder
    usedAt?: SortOrder
    createdAt?: SortOrder
  }

  export type AppSettingsCountOrderByAggregateInput = {
    id?: SortOrder
    brandName?: SortOrder
    brandLogoUrl?: SortOrder
    brandLogoUrlDark?: SortOrder
    brandTagline?: SortOrder
    customCss?: SortOrder
    primaryColor?: SortOrder
    accentColor?: SortOrder
    emailButtonColor?: SortOrder
    loginBgColor?: SortOrder
    loginCardColor?: SortOrder
    loginTextColor?: SortOrder
    loginInputColor?: SortOrder
    loginRingColor?: SortOrder
    loginBgColorDark?: SortOrder
    loginCardColorDark?: SortOrder
    loginTextColorDark?: SortOrder
    loginInputColorDark?: SortOrder
    loginRingColorDark?: SortOrder
    sidebarBgColor?: SortOrder
    sidebarTextColor?: SortOrder
    sidebarAccentColor?: SortOrder
    faviconUrl?: SortOrder
    loginHeading?: SortOrder
    loginSubheading?: SortOrder
    disabledPlugins?: SortOrder
    updatedAt?: SortOrder
  }

  export type AppSettingsMaxOrderByAggregateInput = {
    id?: SortOrder
    brandName?: SortOrder
    brandLogoUrl?: SortOrder
    brandLogoUrlDark?: SortOrder
    brandTagline?: SortOrder
    customCss?: SortOrder
    primaryColor?: SortOrder
    accentColor?: SortOrder
    emailButtonColor?: SortOrder
    loginBgColor?: SortOrder
    loginCardColor?: SortOrder
    loginTextColor?: SortOrder
    loginInputColor?: SortOrder
    loginRingColor?: SortOrder
    loginBgColorDark?: SortOrder
    loginCardColorDark?: SortOrder
    loginTextColorDark?: SortOrder
    loginInputColorDark?: SortOrder
    loginRingColorDark?: SortOrder
    sidebarBgColor?: SortOrder
    sidebarTextColor?: SortOrder
    sidebarAccentColor?: SortOrder
    faviconUrl?: SortOrder
    loginHeading?: SortOrder
    loginSubheading?: SortOrder
    disabledPlugins?: SortOrder
    updatedAt?: SortOrder
  }

  export type AppSettingsMinOrderByAggregateInput = {
    id?: SortOrder
    brandName?: SortOrder
    brandLogoUrl?: SortOrder
    brandLogoUrlDark?: SortOrder
    brandTagline?: SortOrder
    customCss?: SortOrder
    primaryColor?: SortOrder
    accentColor?: SortOrder
    emailButtonColor?: SortOrder
    loginBgColor?: SortOrder
    loginCardColor?: SortOrder
    loginTextColor?: SortOrder
    loginInputColor?: SortOrder
    loginRingColor?: SortOrder
    loginBgColorDark?: SortOrder
    loginCardColorDark?: SortOrder
    loginTextColorDark?: SortOrder
    loginInputColorDark?: SortOrder
    loginRingColorDark?: SortOrder
    sidebarBgColor?: SortOrder
    sidebarTextColor?: SortOrder
    sidebarAccentColor?: SortOrder
    faviconUrl?: SortOrder
    loginHeading?: SortOrder
    loginSubheading?: SortOrder
    disabledPlugins?: SortOrder
    updatedAt?: SortOrder
  }

  export type AuditLogCountOrderByAggregateInput = {
    id?: SortOrder
    tenantId?: SortOrder
    userId?: SortOrder
    action?: SortOrder
    entity?: SortOrder
    entityId?: SortOrder
    metadata?: SortOrder
    ipAddress?: SortOrder
    createdAt?: SortOrder
    impersonatedBy?: SortOrder
  }

  export type AuditLogMaxOrderByAggregateInput = {
    id?: SortOrder
    tenantId?: SortOrder
    userId?: SortOrder
    action?: SortOrder
    entity?: SortOrder
    entityId?: SortOrder
    ipAddress?: SortOrder
    createdAt?: SortOrder
    impersonatedBy?: SortOrder
  }

  export type AuditLogMinOrderByAggregateInput = {
    id?: SortOrder
    tenantId?: SortOrder
    userId?: SortOrder
    action?: SortOrder
    entity?: SortOrder
    entityId?: SortOrder
    ipAddress?: SortOrder
    createdAt?: SortOrder
    impersonatedBy?: SortOrder
  }

  export type EnumWaitlistStatusFilter<$PrismaModel = never> = {
    equals?: $Enums.WaitlistStatus | EnumWaitlistStatusFieldRefInput<$PrismaModel>
    in?: $Enums.WaitlistStatus[] | ListEnumWaitlistStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.WaitlistStatus[] | ListEnumWaitlistStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumWaitlistStatusFilter<$PrismaModel> | $Enums.WaitlistStatus
  }

  export type WaitlistEntryCountOrderByAggregateInput = {
    id?: SortOrder
    email?: SortOrder
    name?: SortOrder
    company?: SortOrder
    useCase?: SortOrder
    status?: SortOrder
    promotedAt?: SortOrder
    createdAt?: SortOrder
  }

  export type WaitlistEntryMaxOrderByAggregateInput = {
    id?: SortOrder
    email?: SortOrder
    name?: SortOrder
    company?: SortOrder
    useCase?: SortOrder
    status?: SortOrder
    promotedAt?: SortOrder
    createdAt?: SortOrder
  }

  export type WaitlistEntryMinOrderByAggregateInput = {
    id?: SortOrder
    email?: SortOrder
    name?: SortOrder
    company?: SortOrder
    useCase?: SortOrder
    status?: SortOrder
    promotedAt?: SortOrder
    createdAt?: SortOrder
  }

  export type EnumWaitlistStatusWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.WaitlistStatus | EnumWaitlistStatusFieldRefInput<$PrismaModel>
    in?: $Enums.WaitlistStatus[] | ListEnumWaitlistStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.WaitlistStatus[] | ListEnumWaitlistStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumWaitlistStatusWithAggregatesFilter<$PrismaModel> | $Enums.WaitlistStatus
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumWaitlistStatusFilter<$PrismaModel>
    _max?: NestedEnumWaitlistStatusFilter<$PrismaModel>
  }

  export type IntFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel>
    in?: number[] | ListIntFieldRefInput<$PrismaModel>
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel>
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntFilter<$PrismaModel> | number
  }

  export type AnnotationCountOrderByAggregateInput = {
    id?: SortOrder
    jobId?: SortOrder
    tenantId?: SortOrder
    pageNum?: SortOrder
    authorId?: SortOrder
    authorEmail?: SortOrder
    authorName?: SortOrder
    fabricJson?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type AnnotationAvgOrderByAggregateInput = {
    pageNum?: SortOrder
  }

  export type AnnotationMaxOrderByAggregateInput = {
    id?: SortOrder
    jobId?: SortOrder
    tenantId?: SortOrder
    pageNum?: SortOrder
    authorId?: SortOrder
    authorEmail?: SortOrder
    authorName?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type AnnotationMinOrderByAggregateInput = {
    id?: SortOrder
    jobId?: SortOrder
    tenantId?: SortOrder
    pageNum?: SortOrder
    authorId?: SortOrder
    authorEmail?: SortOrder
    authorName?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type AnnotationSumOrderByAggregateInput = {
    pageNum?: SortOrder
  }

  export type IntWithAggregatesFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel>
    in?: number[] | ListIntFieldRefInput<$PrismaModel>
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel>
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntWithAggregatesFilter<$PrismaModel> | number
    _count?: NestedIntFilter<$PrismaModel>
    _avg?: NestedFloatFilter<$PrismaModel>
    _sum?: NestedIntFilter<$PrismaModel>
    _min?: NestedIntFilter<$PrismaModel>
    _max?: NestedIntFilter<$PrismaModel>
  }

  export type ReportViewCountOrderByAggregateInput = {
    id?: SortOrder
    jobId?: SortOrder
    tenantId?: SortOrder
    reportToken?: SortOrder
    viewerEmail?: SortOrder
    viewerName?: SortOrder
    ipAddress?: SortOrder
    userAgent?: SortOrder
    viewedAt?: SortOrder
  }

  export type ReportViewMaxOrderByAggregateInput = {
    id?: SortOrder
    jobId?: SortOrder
    tenantId?: SortOrder
    reportToken?: SortOrder
    viewerEmail?: SortOrder
    viewerName?: SortOrder
    ipAddress?: SortOrder
    userAgent?: SortOrder
    viewedAt?: SortOrder
  }

  export type ReportViewMinOrderByAggregateInput = {
    id?: SortOrder
    jobId?: SortOrder
    tenantId?: SortOrder
    reportToken?: SortOrder
    viewerEmail?: SortOrder
    viewerName?: SortOrder
    ipAddress?: SortOrder
    userAgent?: SortOrder
    viewedAt?: SortOrder
  }

  export type TenantUserCreateNestedManyWithoutTenantInput = {
    create?: XOR<TenantUserCreateWithoutTenantInput, TenantUserUncheckedCreateWithoutTenantInput> | TenantUserCreateWithoutTenantInput[] | TenantUserUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: TenantUserCreateOrConnectWithoutTenantInput | TenantUserCreateOrConnectWithoutTenantInput[]
    createMany?: TenantUserCreateManyTenantInputEnvelope
    connect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
  }

  export type TenantInviteCreateNestedManyWithoutTenantInput = {
    create?: XOR<TenantInviteCreateWithoutTenantInput, TenantInviteUncheckedCreateWithoutTenantInput> | TenantInviteCreateWithoutTenantInput[] | TenantInviteUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: TenantInviteCreateOrConnectWithoutTenantInput | TenantInviteCreateOrConnectWithoutTenantInput[]
    createMany?: TenantInviteCreateManyTenantInputEnvelope
    connect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
  }

  export type AnnotationCreateNestedManyWithoutTenantInput = {
    create?: XOR<AnnotationCreateWithoutTenantInput, AnnotationUncheckedCreateWithoutTenantInput> | AnnotationCreateWithoutTenantInput[] | AnnotationUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: AnnotationCreateOrConnectWithoutTenantInput | AnnotationCreateOrConnectWithoutTenantInput[]
    createMany?: AnnotationCreateManyTenantInputEnvelope
    connect?: AnnotationWhereUniqueInput | AnnotationWhereUniqueInput[]
  }

  export type ReportViewCreateNestedManyWithoutTenantInput = {
    create?: XOR<ReportViewCreateWithoutTenantInput, ReportViewUncheckedCreateWithoutTenantInput> | ReportViewCreateWithoutTenantInput[] | ReportViewUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: ReportViewCreateOrConnectWithoutTenantInput | ReportViewCreateOrConnectWithoutTenantInput[]
    createMany?: ReportViewCreateManyTenantInputEnvelope
    connect?: ReportViewWhereUniqueInput | ReportViewWhereUniqueInput[]
  }

  export type TenantUserUncheckedCreateNestedManyWithoutTenantInput = {
    create?: XOR<TenantUserCreateWithoutTenantInput, TenantUserUncheckedCreateWithoutTenantInput> | TenantUserCreateWithoutTenantInput[] | TenantUserUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: TenantUserCreateOrConnectWithoutTenantInput | TenantUserCreateOrConnectWithoutTenantInput[]
    createMany?: TenantUserCreateManyTenantInputEnvelope
    connect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
  }

  export type TenantInviteUncheckedCreateNestedManyWithoutTenantInput = {
    create?: XOR<TenantInviteCreateWithoutTenantInput, TenantInviteUncheckedCreateWithoutTenantInput> | TenantInviteCreateWithoutTenantInput[] | TenantInviteUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: TenantInviteCreateOrConnectWithoutTenantInput | TenantInviteCreateOrConnectWithoutTenantInput[]
    createMany?: TenantInviteCreateManyTenantInputEnvelope
    connect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
  }

  export type AnnotationUncheckedCreateNestedManyWithoutTenantInput = {
    create?: XOR<AnnotationCreateWithoutTenantInput, AnnotationUncheckedCreateWithoutTenantInput> | AnnotationCreateWithoutTenantInput[] | AnnotationUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: AnnotationCreateOrConnectWithoutTenantInput | AnnotationCreateOrConnectWithoutTenantInput[]
    createMany?: AnnotationCreateManyTenantInputEnvelope
    connect?: AnnotationWhereUniqueInput | AnnotationWhereUniqueInput[]
  }

  export type ReportViewUncheckedCreateNestedManyWithoutTenantInput = {
    create?: XOR<ReportViewCreateWithoutTenantInput, ReportViewUncheckedCreateWithoutTenantInput> | ReportViewCreateWithoutTenantInput[] | ReportViewUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: ReportViewCreateOrConnectWithoutTenantInput | ReportViewCreateOrConnectWithoutTenantInput[]
    createMany?: ReportViewCreateManyTenantInputEnvelope
    connect?: ReportViewWhereUniqueInput | ReportViewWhereUniqueInput[]
  }

  export type StringFieldUpdateOperationsInput = {
    set?: string
  }

  export type NullableStringFieldUpdateOperationsInput = {
    set?: string | null
  }

  export type EnumTenantStatusFieldUpdateOperationsInput = {
    set?: $Enums.TenantStatus
  }

  export type DateTimeFieldUpdateOperationsInput = {
    set?: Date | string
  }

  export type TenantUserUpdateManyWithoutTenantNestedInput = {
    create?: XOR<TenantUserCreateWithoutTenantInput, TenantUserUncheckedCreateWithoutTenantInput> | TenantUserCreateWithoutTenantInput[] | TenantUserUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: TenantUserCreateOrConnectWithoutTenantInput | TenantUserCreateOrConnectWithoutTenantInput[]
    upsert?: TenantUserUpsertWithWhereUniqueWithoutTenantInput | TenantUserUpsertWithWhereUniqueWithoutTenantInput[]
    createMany?: TenantUserCreateManyTenantInputEnvelope
    set?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    disconnect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    delete?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    connect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    update?: TenantUserUpdateWithWhereUniqueWithoutTenantInput | TenantUserUpdateWithWhereUniqueWithoutTenantInput[]
    updateMany?: TenantUserUpdateManyWithWhereWithoutTenantInput | TenantUserUpdateManyWithWhereWithoutTenantInput[]
    deleteMany?: TenantUserScalarWhereInput | TenantUserScalarWhereInput[]
  }

  export type TenantInviteUpdateManyWithoutTenantNestedInput = {
    create?: XOR<TenantInviteCreateWithoutTenantInput, TenantInviteUncheckedCreateWithoutTenantInput> | TenantInviteCreateWithoutTenantInput[] | TenantInviteUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: TenantInviteCreateOrConnectWithoutTenantInput | TenantInviteCreateOrConnectWithoutTenantInput[]
    upsert?: TenantInviteUpsertWithWhereUniqueWithoutTenantInput | TenantInviteUpsertWithWhereUniqueWithoutTenantInput[]
    createMany?: TenantInviteCreateManyTenantInputEnvelope
    set?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    disconnect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    delete?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    connect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    update?: TenantInviteUpdateWithWhereUniqueWithoutTenantInput | TenantInviteUpdateWithWhereUniqueWithoutTenantInput[]
    updateMany?: TenantInviteUpdateManyWithWhereWithoutTenantInput | TenantInviteUpdateManyWithWhereWithoutTenantInput[]
    deleteMany?: TenantInviteScalarWhereInput | TenantInviteScalarWhereInput[]
  }

  export type AnnotationUpdateManyWithoutTenantNestedInput = {
    create?: XOR<AnnotationCreateWithoutTenantInput, AnnotationUncheckedCreateWithoutTenantInput> | AnnotationCreateWithoutTenantInput[] | AnnotationUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: AnnotationCreateOrConnectWithoutTenantInput | AnnotationCreateOrConnectWithoutTenantInput[]
    upsert?: AnnotationUpsertWithWhereUniqueWithoutTenantInput | AnnotationUpsertWithWhereUniqueWithoutTenantInput[]
    createMany?: AnnotationCreateManyTenantInputEnvelope
    set?: AnnotationWhereUniqueInput | AnnotationWhereUniqueInput[]
    disconnect?: AnnotationWhereUniqueInput | AnnotationWhereUniqueInput[]
    delete?: AnnotationWhereUniqueInput | AnnotationWhereUniqueInput[]
    connect?: AnnotationWhereUniqueInput | AnnotationWhereUniqueInput[]
    update?: AnnotationUpdateWithWhereUniqueWithoutTenantInput | AnnotationUpdateWithWhereUniqueWithoutTenantInput[]
    updateMany?: AnnotationUpdateManyWithWhereWithoutTenantInput | AnnotationUpdateManyWithWhereWithoutTenantInput[]
    deleteMany?: AnnotationScalarWhereInput | AnnotationScalarWhereInput[]
  }

  export type ReportViewUpdateManyWithoutTenantNestedInput = {
    create?: XOR<ReportViewCreateWithoutTenantInput, ReportViewUncheckedCreateWithoutTenantInput> | ReportViewCreateWithoutTenantInput[] | ReportViewUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: ReportViewCreateOrConnectWithoutTenantInput | ReportViewCreateOrConnectWithoutTenantInput[]
    upsert?: ReportViewUpsertWithWhereUniqueWithoutTenantInput | ReportViewUpsertWithWhereUniqueWithoutTenantInput[]
    createMany?: ReportViewCreateManyTenantInputEnvelope
    set?: ReportViewWhereUniqueInput | ReportViewWhereUniqueInput[]
    disconnect?: ReportViewWhereUniqueInput | ReportViewWhereUniqueInput[]
    delete?: ReportViewWhereUniqueInput | ReportViewWhereUniqueInput[]
    connect?: ReportViewWhereUniqueInput | ReportViewWhereUniqueInput[]
    update?: ReportViewUpdateWithWhereUniqueWithoutTenantInput | ReportViewUpdateWithWhereUniqueWithoutTenantInput[]
    updateMany?: ReportViewUpdateManyWithWhereWithoutTenantInput | ReportViewUpdateManyWithWhereWithoutTenantInput[]
    deleteMany?: ReportViewScalarWhereInput | ReportViewScalarWhereInput[]
  }

  export type TenantUserUncheckedUpdateManyWithoutTenantNestedInput = {
    create?: XOR<TenantUserCreateWithoutTenantInput, TenantUserUncheckedCreateWithoutTenantInput> | TenantUserCreateWithoutTenantInput[] | TenantUserUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: TenantUserCreateOrConnectWithoutTenantInput | TenantUserCreateOrConnectWithoutTenantInput[]
    upsert?: TenantUserUpsertWithWhereUniqueWithoutTenantInput | TenantUserUpsertWithWhereUniqueWithoutTenantInput[]
    createMany?: TenantUserCreateManyTenantInputEnvelope
    set?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    disconnect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    delete?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    connect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    update?: TenantUserUpdateWithWhereUniqueWithoutTenantInput | TenantUserUpdateWithWhereUniqueWithoutTenantInput[]
    updateMany?: TenantUserUpdateManyWithWhereWithoutTenantInput | TenantUserUpdateManyWithWhereWithoutTenantInput[]
    deleteMany?: TenantUserScalarWhereInput | TenantUserScalarWhereInput[]
  }

  export type TenantInviteUncheckedUpdateManyWithoutTenantNestedInput = {
    create?: XOR<TenantInviteCreateWithoutTenantInput, TenantInviteUncheckedCreateWithoutTenantInput> | TenantInviteCreateWithoutTenantInput[] | TenantInviteUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: TenantInviteCreateOrConnectWithoutTenantInput | TenantInviteCreateOrConnectWithoutTenantInput[]
    upsert?: TenantInviteUpsertWithWhereUniqueWithoutTenantInput | TenantInviteUpsertWithWhereUniqueWithoutTenantInput[]
    createMany?: TenantInviteCreateManyTenantInputEnvelope
    set?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    disconnect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    delete?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    connect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    update?: TenantInviteUpdateWithWhereUniqueWithoutTenantInput | TenantInviteUpdateWithWhereUniqueWithoutTenantInput[]
    updateMany?: TenantInviteUpdateManyWithWhereWithoutTenantInput | TenantInviteUpdateManyWithWhereWithoutTenantInput[]
    deleteMany?: TenantInviteScalarWhereInput | TenantInviteScalarWhereInput[]
  }

  export type AnnotationUncheckedUpdateManyWithoutTenantNestedInput = {
    create?: XOR<AnnotationCreateWithoutTenantInput, AnnotationUncheckedCreateWithoutTenantInput> | AnnotationCreateWithoutTenantInput[] | AnnotationUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: AnnotationCreateOrConnectWithoutTenantInput | AnnotationCreateOrConnectWithoutTenantInput[]
    upsert?: AnnotationUpsertWithWhereUniqueWithoutTenantInput | AnnotationUpsertWithWhereUniqueWithoutTenantInput[]
    createMany?: AnnotationCreateManyTenantInputEnvelope
    set?: AnnotationWhereUniqueInput | AnnotationWhereUniqueInput[]
    disconnect?: AnnotationWhereUniqueInput | AnnotationWhereUniqueInput[]
    delete?: AnnotationWhereUniqueInput | AnnotationWhereUniqueInput[]
    connect?: AnnotationWhereUniqueInput | AnnotationWhereUniqueInput[]
    update?: AnnotationUpdateWithWhereUniqueWithoutTenantInput | AnnotationUpdateWithWhereUniqueWithoutTenantInput[]
    updateMany?: AnnotationUpdateManyWithWhereWithoutTenantInput | AnnotationUpdateManyWithWhereWithoutTenantInput[]
    deleteMany?: AnnotationScalarWhereInput | AnnotationScalarWhereInput[]
  }

  export type ReportViewUncheckedUpdateManyWithoutTenantNestedInput = {
    create?: XOR<ReportViewCreateWithoutTenantInput, ReportViewUncheckedCreateWithoutTenantInput> | ReportViewCreateWithoutTenantInput[] | ReportViewUncheckedCreateWithoutTenantInput[]
    connectOrCreate?: ReportViewCreateOrConnectWithoutTenantInput | ReportViewCreateOrConnectWithoutTenantInput[]
    upsert?: ReportViewUpsertWithWhereUniqueWithoutTenantInput | ReportViewUpsertWithWhereUniqueWithoutTenantInput[]
    createMany?: ReportViewCreateManyTenantInputEnvelope
    set?: ReportViewWhereUniqueInput | ReportViewWhereUniqueInput[]
    disconnect?: ReportViewWhereUniqueInput | ReportViewWhereUniqueInput[]
    delete?: ReportViewWhereUniqueInput | ReportViewWhereUniqueInput[]
    connect?: ReportViewWhereUniqueInput | ReportViewWhereUniqueInput[]
    update?: ReportViewUpdateWithWhereUniqueWithoutTenantInput | ReportViewUpdateWithWhereUniqueWithoutTenantInput[]
    updateMany?: ReportViewUpdateManyWithWhereWithoutTenantInput | ReportViewUpdateManyWithWhereWithoutTenantInput[]
    deleteMany?: ReportViewScalarWhereInput | ReportViewScalarWhereInput[]
  }

  export type TenantUserCreateNestedManyWithoutUserInput = {
    create?: XOR<TenantUserCreateWithoutUserInput, TenantUserUncheckedCreateWithoutUserInput> | TenantUserCreateWithoutUserInput[] | TenantUserUncheckedCreateWithoutUserInput[]
    connectOrCreate?: TenantUserCreateOrConnectWithoutUserInput | TenantUserCreateOrConnectWithoutUserInput[]
    createMany?: TenantUserCreateManyUserInputEnvelope
    connect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
  }

  export type SessionCreateNestedManyWithoutUserInput = {
    create?: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput> | SessionCreateWithoutUserInput[] | SessionUncheckedCreateWithoutUserInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutUserInput | SessionCreateOrConnectWithoutUserInput[]
    createMany?: SessionCreateManyUserInputEnvelope
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
  }

  export type MagicLinkCreateNestedManyWithoutUserInput = {
    create?: XOR<MagicLinkCreateWithoutUserInput, MagicLinkUncheckedCreateWithoutUserInput> | MagicLinkCreateWithoutUserInput[] | MagicLinkUncheckedCreateWithoutUserInput[]
    connectOrCreate?: MagicLinkCreateOrConnectWithoutUserInput | MagicLinkCreateOrConnectWithoutUserInput[]
    createMany?: MagicLinkCreateManyUserInputEnvelope
    connect?: MagicLinkWhereUniqueInput | MagicLinkWhereUniqueInput[]
  }

  export type TenantInviteCreateNestedManyWithoutUserInput = {
    create?: XOR<TenantInviteCreateWithoutUserInput, TenantInviteUncheckedCreateWithoutUserInput> | TenantInviteCreateWithoutUserInput[] | TenantInviteUncheckedCreateWithoutUserInput[]
    connectOrCreate?: TenantInviteCreateOrConnectWithoutUserInput | TenantInviteCreateOrConnectWithoutUserInput[]
    createMany?: TenantInviteCreateManyUserInputEnvelope
    connect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
  }

  export type TenantUserUncheckedCreateNestedManyWithoutUserInput = {
    create?: XOR<TenantUserCreateWithoutUserInput, TenantUserUncheckedCreateWithoutUserInput> | TenantUserCreateWithoutUserInput[] | TenantUserUncheckedCreateWithoutUserInput[]
    connectOrCreate?: TenantUserCreateOrConnectWithoutUserInput | TenantUserCreateOrConnectWithoutUserInput[]
    createMany?: TenantUserCreateManyUserInputEnvelope
    connect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
  }

  export type SessionUncheckedCreateNestedManyWithoutUserInput = {
    create?: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput> | SessionCreateWithoutUserInput[] | SessionUncheckedCreateWithoutUserInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutUserInput | SessionCreateOrConnectWithoutUserInput[]
    createMany?: SessionCreateManyUserInputEnvelope
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
  }

  export type MagicLinkUncheckedCreateNestedManyWithoutUserInput = {
    create?: XOR<MagicLinkCreateWithoutUserInput, MagicLinkUncheckedCreateWithoutUserInput> | MagicLinkCreateWithoutUserInput[] | MagicLinkUncheckedCreateWithoutUserInput[]
    connectOrCreate?: MagicLinkCreateOrConnectWithoutUserInput | MagicLinkCreateOrConnectWithoutUserInput[]
    createMany?: MagicLinkCreateManyUserInputEnvelope
    connect?: MagicLinkWhereUniqueInput | MagicLinkWhereUniqueInput[]
  }

  export type TenantInviteUncheckedCreateNestedManyWithoutUserInput = {
    create?: XOR<TenantInviteCreateWithoutUserInput, TenantInviteUncheckedCreateWithoutUserInput> | TenantInviteCreateWithoutUserInput[] | TenantInviteUncheckedCreateWithoutUserInput[]
    connectOrCreate?: TenantInviteCreateOrConnectWithoutUserInput | TenantInviteCreateOrConnectWithoutUserInput[]
    createMany?: TenantInviteCreateManyUserInputEnvelope
    connect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
  }

  export type BoolFieldUpdateOperationsInput = {
    set?: boolean
  }

  export type TenantUserUpdateManyWithoutUserNestedInput = {
    create?: XOR<TenantUserCreateWithoutUserInput, TenantUserUncheckedCreateWithoutUserInput> | TenantUserCreateWithoutUserInput[] | TenantUserUncheckedCreateWithoutUserInput[]
    connectOrCreate?: TenantUserCreateOrConnectWithoutUserInput | TenantUserCreateOrConnectWithoutUserInput[]
    upsert?: TenantUserUpsertWithWhereUniqueWithoutUserInput | TenantUserUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: TenantUserCreateManyUserInputEnvelope
    set?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    disconnect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    delete?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    connect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    update?: TenantUserUpdateWithWhereUniqueWithoutUserInput | TenantUserUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: TenantUserUpdateManyWithWhereWithoutUserInput | TenantUserUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: TenantUserScalarWhereInput | TenantUserScalarWhereInput[]
  }

  export type SessionUpdateManyWithoutUserNestedInput = {
    create?: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput> | SessionCreateWithoutUserInput[] | SessionUncheckedCreateWithoutUserInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutUserInput | SessionCreateOrConnectWithoutUserInput[]
    upsert?: SessionUpsertWithWhereUniqueWithoutUserInput | SessionUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: SessionCreateManyUserInputEnvelope
    set?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    disconnect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    delete?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    update?: SessionUpdateWithWhereUniqueWithoutUserInput | SessionUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: SessionUpdateManyWithWhereWithoutUserInput | SessionUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: SessionScalarWhereInput | SessionScalarWhereInput[]
  }

  export type MagicLinkUpdateManyWithoutUserNestedInput = {
    create?: XOR<MagicLinkCreateWithoutUserInput, MagicLinkUncheckedCreateWithoutUserInput> | MagicLinkCreateWithoutUserInput[] | MagicLinkUncheckedCreateWithoutUserInput[]
    connectOrCreate?: MagicLinkCreateOrConnectWithoutUserInput | MagicLinkCreateOrConnectWithoutUserInput[]
    upsert?: MagicLinkUpsertWithWhereUniqueWithoutUserInput | MagicLinkUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: MagicLinkCreateManyUserInputEnvelope
    set?: MagicLinkWhereUniqueInput | MagicLinkWhereUniqueInput[]
    disconnect?: MagicLinkWhereUniqueInput | MagicLinkWhereUniqueInput[]
    delete?: MagicLinkWhereUniqueInput | MagicLinkWhereUniqueInput[]
    connect?: MagicLinkWhereUniqueInput | MagicLinkWhereUniqueInput[]
    update?: MagicLinkUpdateWithWhereUniqueWithoutUserInput | MagicLinkUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: MagicLinkUpdateManyWithWhereWithoutUserInput | MagicLinkUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: MagicLinkScalarWhereInput | MagicLinkScalarWhereInput[]
  }

  export type TenantInviteUpdateManyWithoutUserNestedInput = {
    create?: XOR<TenantInviteCreateWithoutUserInput, TenantInviteUncheckedCreateWithoutUserInput> | TenantInviteCreateWithoutUserInput[] | TenantInviteUncheckedCreateWithoutUserInput[]
    connectOrCreate?: TenantInviteCreateOrConnectWithoutUserInput | TenantInviteCreateOrConnectWithoutUserInput[]
    upsert?: TenantInviteUpsertWithWhereUniqueWithoutUserInput | TenantInviteUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: TenantInviteCreateManyUserInputEnvelope
    set?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    disconnect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    delete?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    connect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    update?: TenantInviteUpdateWithWhereUniqueWithoutUserInput | TenantInviteUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: TenantInviteUpdateManyWithWhereWithoutUserInput | TenantInviteUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: TenantInviteScalarWhereInput | TenantInviteScalarWhereInput[]
  }

  export type TenantUserUncheckedUpdateManyWithoutUserNestedInput = {
    create?: XOR<TenantUserCreateWithoutUserInput, TenantUserUncheckedCreateWithoutUserInput> | TenantUserCreateWithoutUserInput[] | TenantUserUncheckedCreateWithoutUserInput[]
    connectOrCreate?: TenantUserCreateOrConnectWithoutUserInput | TenantUserCreateOrConnectWithoutUserInput[]
    upsert?: TenantUserUpsertWithWhereUniqueWithoutUserInput | TenantUserUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: TenantUserCreateManyUserInputEnvelope
    set?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    disconnect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    delete?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    connect?: TenantUserWhereUniqueInput | TenantUserWhereUniqueInput[]
    update?: TenantUserUpdateWithWhereUniqueWithoutUserInput | TenantUserUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: TenantUserUpdateManyWithWhereWithoutUserInput | TenantUserUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: TenantUserScalarWhereInput | TenantUserScalarWhereInput[]
  }

  export type SessionUncheckedUpdateManyWithoutUserNestedInput = {
    create?: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput> | SessionCreateWithoutUserInput[] | SessionUncheckedCreateWithoutUserInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutUserInput | SessionCreateOrConnectWithoutUserInput[]
    upsert?: SessionUpsertWithWhereUniqueWithoutUserInput | SessionUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: SessionCreateManyUserInputEnvelope
    set?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    disconnect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    delete?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    update?: SessionUpdateWithWhereUniqueWithoutUserInput | SessionUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: SessionUpdateManyWithWhereWithoutUserInput | SessionUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: SessionScalarWhereInput | SessionScalarWhereInput[]
  }

  export type MagicLinkUncheckedUpdateManyWithoutUserNestedInput = {
    create?: XOR<MagicLinkCreateWithoutUserInput, MagicLinkUncheckedCreateWithoutUserInput> | MagicLinkCreateWithoutUserInput[] | MagicLinkUncheckedCreateWithoutUserInput[]
    connectOrCreate?: MagicLinkCreateOrConnectWithoutUserInput | MagicLinkCreateOrConnectWithoutUserInput[]
    upsert?: MagicLinkUpsertWithWhereUniqueWithoutUserInput | MagicLinkUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: MagicLinkCreateManyUserInputEnvelope
    set?: MagicLinkWhereUniqueInput | MagicLinkWhereUniqueInput[]
    disconnect?: MagicLinkWhereUniqueInput | MagicLinkWhereUniqueInput[]
    delete?: MagicLinkWhereUniqueInput | MagicLinkWhereUniqueInput[]
    connect?: MagicLinkWhereUniqueInput | MagicLinkWhereUniqueInput[]
    update?: MagicLinkUpdateWithWhereUniqueWithoutUserInput | MagicLinkUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: MagicLinkUpdateManyWithWhereWithoutUserInput | MagicLinkUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: MagicLinkScalarWhereInput | MagicLinkScalarWhereInput[]
  }

  export type TenantInviteUncheckedUpdateManyWithoutUserNestedInput = {
    create?: XOR<TenantInviteCreateWithoutUserInput, TenantInviteUncheckedCreateWithoutUserInput> | TenantInviteCreateWithoutUserInput[] | TenantInviteUncheckedCreateWithoutUserInput[]
    connectOrCreate?: TenantInviteCreateOrConnectWithoutUserInput | TenantInviteCreateOrConnectWithoutUserInput[]
    upsert?: TenantInviteUpsertWithWhereUniqueWithoutUserInput | TenantInviteUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: TenantInviteCreateManyUserInputEnvelope
    set?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    disconnect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    delete?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    connect?: TenantInviteWhereUniqueInput | TenantInviteWhereUniqueInput[]
    update?: TenantInviteUpdateWithWhereUniqueWithoutUserInput | TenantInviteUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: TenantInviteUpdateManyWithWhereWithoutUserInput | TenantInviteUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: TenantInviteScalarWhereInput | TenantInviteScalarWhereInput[]
  }

  export type UserCreateNestedOneWithoutTenantsInput = {
    create?: XOR<UserCreateWithoutTenantsInput, UserUncheckedCreateWithoutTenantsInput>
    connectOrCreate?: UserCreateOrConnectWithoutTenantsInput
    connect?: UserWhereUniqueInput
  }

  export type TenantCreateNestedOneWithoutUsersInput = {
    create?: XOR<TenantCreateWithoutUsersInput, TenantUncheckedCreateWithoutUsersInput>
    connectOrCreate?: TenantCreateOrConnectWithoutUsersInput
    connect?: TenantWhereUniqueInput
  }

  export type EnumTenantRoleFieldUpdateOperationsInput = {
    set?: $Enums.TenantRole
  }

  export type UserUpdateOneRequiredWithoutTenantsNestedInput = {
    create?: XOR<UserCreateWithoutTenantsInput, UserUncheckedCreateWithoutTenantsInput>
    connectOrCreate?: UserCreateOrConnectWithoutTenantsInput
    upsert?: UserUpsertWithoutTenantsInput
    connect?: UserWhereUniqueInput
    update?: XOR<XOR<UserUpdateToOneWithWhereWithoutTenantsInput, UserUpdateWithoutTenantsInput>, UserUncheckedUpdateWithoutTenantsInput>
  }

  export type TenantUpdateOneRequiredWithoutUsersNestedInput = {
    create?: XOR<TenantCreateWithoutUsersInput, TenantUncheckedCreateWithoutUsersInput>
    connectOrCreate?: TenantCreateOrConnectWithoutUsersInput
    upsert?: TenantUpsertWithoutUsersInput
    connect?: TenantWhereUniqueInput
    update?: XOR<XOR<TenantUpdateToOneWithWhereWithoutUsersInput, TenantUpdateWithoutUsersInput>, TenantUncheckedUpdateWithoutUsersInput>
  }

  export type TenantCreateNestedOneWithoutInvitesInput = {
    create?: XOR<TenantCreateWithoutInvitesInput, TenantUncheckedCreateWithoutInvitesInput>
    connectOrCreate?: TenantCreateOrConnectWithoutInvitesInput
    connect?: TenantWhereUniqueInput
  }

  export type UserCreateNestedOneWithoutInvitesInput = {
    create?: XOR<UserCreateWithoutInvitesInput, UserUncheckedCreateWithoutInvitesInput>
    connectOrCreate?: UserCreateOrConnectWithoutInvitesInput
    connect?: UserWhereUniqueInput
  }

  export type NullableDateTimeFieldUpdateOperationsInput = {
    set?: Date | string | null
  }

  export type TenantUpdateOneRequiredWithoutInvitesNestedInput = {
    create?: XOR<TenantCreateWithoutInvitesInput, TenantUncheckedCreateWithoutInvitesInput>
    connectOrCreate?: TenantCreateOrConnectWithoutInvitesInput
    upsert?: TenantUpsertWithoutInvitesInput
    connect?: TenantWhereUniqueInput
    update?: XOR<XOR<TenantUpdateToOneWithWhereWithoutInvitesInput, TenantUpdateWithoutInvitesInput>, TenantUncheckedUpdateWithoutInvitesInput>
  }

  export type UserUpdateOneRequiredWithoutInvitesNestedInput = {
    create?: XOR<UserCreateWithoutInvitesInput, UserUncheckedCreateWithoutInvitesInput>
    connectOrCreate?: UserCreateOrConnectWithoutInvitesInput
    upsert?: UserUpsertWithoutInvitesInput
    connect?: UserWhereUniqueInput
    update?: XOR<XOR<UserUpdateToOneWithWhereWithoutInvitesInput, UserUpdateWithoutInvitesInput>, UserUncheckedUpdateWithoutInvitesInput>
  }

  export type UserCreateNestedOneWithoutSessionsInput = {
    create?: XOR<UserCreateWithoutSessionsInput, UserUncheckedCreateWithoutSessionsInput>
    connectOrCreate?: UserCreateOrConnectWithoutSessionsInput
    connect?: UserWhereUniqueInput
  }

  export type UserUpdateOneRequiredWithoutSessionsNestedInput = {
    create?: XOR<UserCreateWithoutSessionsInput, UserUncheckedCreateWithoutSessionsInput>
    connectOrCreate?: UserCreateOrConnectWithoutSessionsInput
    upsert?: UserUpsertWithoutSessionsInput
    connect?: UserWhereUniqueInput
    update?: XOR<XOR<UserUpdateToOneWithWhereWithoutSessionsInput, UserUpdateWithoutSessionsInput>, UserUncheckedUpdateWithoutSessionsInput>
  }

  export type UserCreateNestedOneWithoutMagicLinksInput = {
    create?: XOR<UserCreateWithoutMagicLinksInput, UserUncheckedCreateWithoutMagicLinksInput>
    connectOrCreate?: UserCreateOrConnectWithoutMagicLinksInput
    connect?: UserWhereUniqueInput
  }

  export type UserUpdateOneRequiredWithoutMagicLinksNestedInput = {
    create?: XOR<UserCreateWithoutMagicLinksInput, UserUncheckedCreateWithoutMagicLinksInput>
    connectOrCreate?: UserCreateOrConnectWithoutMagicLinksInput
    upsert?: UserUpsertWithoutMagicLinksInput
    connect?: UserWhereUniqueInput
    update?: XOR<XOR<UserUpdateToOneWithWhereWithoutMagicLinksInput, UserUpdateWithoutMagicLinksInput>, UserUncheckedUpdateWithoutMagicLinksInput>
  }

  export type EnumWaitlistStatusFieldUpdateOperationsInput = {
    set?: $Enums.WaitlistStatus
  }

  export type TenantCreateNestedOneWithoutAnnotationsInput = {
    create?: XOR<TenantCreateWithoutAnnotationsInput, TenantUncheckedCreateWithoutAnnotationsInput>
    connectOrCreate?: TenantCreateOrConnectWithoutAnnotationsInput
    connect?: TenantWhereUniqueInput
  }

  export type IntFieldUpdateOperationsInput = {
    set?: number
    increment?: number
    decrement?: number
    multiply?: number
    divide?: number
  }

  export type TenantUpdateOneRequiredWithoutAnnotationsNestedInput = {
    create?: XOR<TenantCreateWithoutAnnotationsInput, TenantUncheckedCreateWithoutAnnotationsInput>
    connectOrCreate?: TenantCreateOrConnectWithoutAnnotationsInput
    upsert?: TenantUpsertWithoutAnnotationsInput
    connect?: TenantWhereUniqueInput
    update?: XOR<XOR<TenantUpdateToOneWithWhereWithoutAnnotationsInput, TenantUpdateWithoutAnnotationsInput>, TenantUncheckedUpdateWithoutAnnotationsInput>
  }

  export type TenantCreateNestedOneWithoutReportViewsInput = {
    create?: XOR<TenantCreateWithoutReportViewsInput, TenantUncheckedCreateWithoutReportViewsInput>
    connectOrCreate?: TenantCreateOrConnectWithoutReportViewsInput
    connect?: TenantWhereUniqueInput
  }

  export type TenantUpdateOneRequiredWithoutReportViewsNestedInput = {
    create?: XOR<TenantCreateWithoutReportViewsInput, TenantUncheckedCreateWithoutReportViewsInput>
    connectOrCreate?: TenantCreateOrConnectWithoutReportViewsInput
    upsert?: TenantUpsertWithoutReportViewsInput
    connect?: TenantWhereUniqueInput
    update?: XOR<XOR<TenantUpdateToOneWithWhereWithoutReportViewsInput, TenantUpdateWithoutReportViewsInput>, TenantUncheckedUpdateWithoutReportViewsInput>
  }

  export type NestedStringFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringFilter<$PrismaModel> | string
  }

  export type NestedStringNullableFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringNullableFilter<$PrismaModel> | string | null
  }

  export type NestedEnumTenantStatusFilter<$PrismaModel = never> = {
    equals?: $Enums.TenantStatus | EnumTenantStatusFieldRefInput<$PrismaModel>
    in?: $Enums.TenantStatus[] | ListEnumTenantStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.TenantStatus[] | ListEnumTenantStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumTenantStatusFilter<$PrismaModel> | $Enums.TenantStatus
  }

  export type NestedDateTimeFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeFilter<$PrismaModel> | Date | string
  }

  export type NestedStringWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringWithAggregatesFilter<$PrismaModel> | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedStringFilter<$PrismaModel>
    _max?: NestedStringFilter<$PrismaModel>
  }

  export type NestedIntFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel>
    in?: number[] | ListIntFieldRefInput<$PrismaModel>
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel>
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntFilter<$PrismaModel> | number
  }

  export type NestedStringNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringNullableWithAggregatesFilter<$PrismaModel> | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedStringNullableFilter<$PrismaModel>
    _max?: NestedStringNullableFilter<$PrismaModel>
  }

  export type NestedIntNullableFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel> | null
    in?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntNullableFilter<$PrismaModel> | number | null
  }
  export type NestedJsonFilter<$PrismaModel = never> =
    | PatchUndefined<
        Either<Required<NestedJsonFilterBase<$PrismaModel>>, Exclude<keyof Required<NestedJsonFilterBase<$PrismaModel>>, 'path'>>,
        Required<NestedJsonFilterBase<$PrismaModel>>
      >
    | OptionalFlat<Omit<Required<NestedJsonFilterBase<$PrismaModel>>, 'path'>>

  export type NestedJsonFilterBase<$PrismaModel = never> = {
    equals?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
    path?: string[]
    mode?: QueryMode | EnumQueryModeFieldRefInput<$PrismaModel>
    string_contains?: string | StringFieldRefInput<$PrismaModel>
    string_starts_with?: string | StringFieldRefInput<$PrismaModel>
    string_ends_with?: string | StringFieldRefInput<$PrismaModel>
    array_starts_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_ends_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_contains?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    lt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    lte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    not?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
  }

  export type NestedEnumTenantStatusWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.TenantStatus | EnumTenantStatusFieldRefInput<$PrismaModel>
    in?: $Enums.TenantStatus[] | ListEnumTenantStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.TenantStatus[] | ListEnumTenantStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumTenantStatusWithAggregatesFilter<$PrismaModel> | $Enums.TenantStatus
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumTenantStatusFilter<$PrismaModel>
    _max?: NestedEnumTenantStatusFilter<$PrismaModel>
  }

  export type NestedDateTimeWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeWithAggregatesFilter<$PrismaModel> | Date | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedDateTimeFilter<$PrismaModel>
    _max?: NestedDateTimeFilter<$PrismaModel>
  }

  export type NestedBoolFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolFilter<$PrismaModel> | boolean
  }

  export type NestedBoolWithAggregatesFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolWithAggregatesFilter<$PrismaModel> | boolean
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedBoolFilter<$PrismaModel>
    _max?: NestedBoolFilter<$PrismaModel>
  }

  export type NestedEnumTenantRoleFilter<$PrismaModel = never> = {
    equals?: $Enums.TenantRole | EnumTenantRoleFieldRefInput<$PrismaModel>
    in?: $Enums.TenantRole[] | ListEnumTenantRoleFieldRefInput<$PrismaModel>
    notIn?: $Enums.TenantRole[] | ListEnumTenantRoleFieldRefInput<$PrismaModel>
    not?: NestedEnumTenantRoleFilter<$PrismaModel> | $Enums.TenantRole
  }

  export type NestedEnumTenantRoleWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.TenantRole | EnumTenantRoleFieldRefInput<$PrismaModel>
    in?: $Enums.TenantRole[] | ListEnumTenantRoleFieldRefInput<$PrismaModel>
    notIn?: $Enums.TenantRole[] | ListEnumTenantRoleFieldRefInput<$PrismaModel>
    not?: NestedEnumTenantRoleWithAggregatesFilter<$PrismaModel> | $Enums.TenantRole
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumTenantRoleFilter<$PrismaModel>
    _max?: NestedEnumTenantRoleFilter<$PrismaModel>
  }

  export type NestedDateTimeNullableFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableFilter<$PrismaModel> | Date | string | null
  }

  export type NestedDateTimeNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableWithAggregatesFilter<$PrismaModel> | Date | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedDateTimeNullableFilter<$PrismaModel>
    _max?: NestedDateTimeNullableFilter<$PrismaModel>
  }

  export type NestedEnumWaitlistStatusFilter<$PrismaModel = never> = {
    equals?: $Enums.WaitlistStatus | EnumWaitlistStatusFieldRefInput<$PrismaModel>
    in?: $Enums.WaitlistStatus[] | ListEnumWaitlistStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.WaitlistStatus[] | ListEnumWaitlistStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumWaitlistStatusFilter<$PrismaModel> | $Enums.WaitlistStatus
  }

  export type NestedEnumWaitlistStatusWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.WaitlistStatus | EnumWaitlistStatusFieldRefInput<$PrismaModel>
    in?: $Enums.WaitlistStatus[] | ListEnumWaitlistStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.WaitlistStatus[] | ListEnumWaitlistStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumWaitlistStatusWithAggregatesFilter<$PrismaModel> | $Enums.WaitlistStatus
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumWaitlistStatusFilter<$PrismaModel>
    _max?: NestedEnumWaitlistStatusFilter<$PrismaModel>
  }

  export type NestedIntWithAggregatesFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel>
    in?: number[] | ListIntFieldRefInput<$PrismaModel>
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel>
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntWithAggregatesFilter<$PrismaModel> | number
    _count?: NestedIntFilter<$PrismaModel>
    _avg?: NestedFloatFilter<$PrismaModel>
    _sum?: NestedIntFilter<$PrismaModel>
    _min?: NestedIntFilter<$PrismaModel>
    _max?: NestedIntFilter<$PrismaModel>
  }

  export type NestedFloatFilter<$PrismaModel = never> = {
    equals?: number | FloatFieldRefInput<$PrismaModel>
    in?: number[] | ListFloatFieldRefInput<$PrismaModel>
    notIn?: number[] | ListFloatFieldRefInput<$PrismaModel>
    lt?: number | FloatFieldRefInput<$PrismaModel>
    lte?: number | FloatFieldRefInput<$PrismaModel>
    gt?: number | FloatFieldRefInput<$PrismaModel>
    gte?: number | FloatFieldRefInput<$PrismaModel>
    not?: NestedFloatFilter<$PrismaModel> | number
  }

  export type TenantUserCreateWithoutTenantInput = {
    id?: string
    role?: $Enums.TenantRole
    joinedAt?: Date | string
    user: UserCreateNestedOneWithoutTenantsInput
  }

  export type TenantUserUncheckedCreateWithoutTenantInput = {
    id?: string
    userId: string
    role?: $Enums.TenantRole
    joinedAt?: Date | string
  }

  export type TenantUserCreateOrConnectWithoutTenantInput = {
    where: TenantUserWhereUniqueInput
    create: XOR<TenantUserCreateWithoutTenantInput, TenantUserUncheckedCreateWithoutTenantInput>
  }

  export type TenantUserCreateManyTenantInputEnvelope = {
    data: TenantUserCreateManyTenantInput | TenantUserCreateManyTenantInput[]
    skipDuplicates?: boolean
  }

  export type TenantInviteCreateWithoutTenantInput = {
    id?: string
    role?: $Enums.TenantRole
    token: string
    expiresAt: Date | string
    usedAt?: Date | string | null
    acceptedAt?: Date | string | null
    revokedAt?: Date | string | null
    createdAt?: Date | string
    user: UserCreateNestedOneWithoutInvitesInput
  }

  export type TenantInviteUncheckedCreateWithoutTenantInput = {
    id?: string
    email: string
    role?: $Enums.TenantRole
    token: string
    expiresAt: Date | string
    usedAt?: Date | string | null
    acceptedAt?: Date | string | null
    revokedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type TenantInviteCreateOrConnectWithoutTenantInput = {
    where: TenantInviteWhereUniqueInput
    create: XOR<TenantInviteCreateWithoutTenantInput, TenantInviteUncheckedCreateWithoutTenantInput>
  }

  export type TenantInviteCreateManyTenantInputEnvelope = {
    data: TenantInviteCreateManyTenantInput | TenantInviteCreateManyTenantInput[]
    skipDuplicates?: boolean
  }

  export type AnnotationCreateWithoutTenantInput = {
    id?: string
    jobId: string
    pageNum: number
    authorId?: string | null
    authorEmail: string
    authorName?: string | null
    fabricJson: JsonNullValueInput | InputJsonValue
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type AnnotationUncheckedCreateWithoutTenantInput = {
    id?: string
    jobId: string
    pageNum: number
    authorId?: string | null
    authorEmail: string
    authorName?: string | null
    fabricJson: JsonNullValueInput | InputJsonValue
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type AnnotationCreateOrConnectWithoutTenantInput = {
    where: AnnotationWhereUniqueInput
    create: XOR<AnnotationCreateWithoutTenantInput, AnnotationUncheckedCreateWithoutTenantInput>
  }

  export type AnnotationCreateManyTenantInputEnvelope = {
    data: AnnotationCreateManyTenantInput | AnnotationCreateManyTenantInput[]
    skipDuplicates?: boolean
  }

  export type ReportViewCreateWithoutTenantInput = {
    id?: string
    jobId: string
    reportToken: string
    viewerEmail?: string | null
    viewerName?: string | null
    ipAddress?: string | null
    userAgent?: string | null
    viewedAt?: Date | string
  }

  export type ReportViewUncheckedCreateWithoutTenantInput = {
    id?: string
    jobId: string
    reportToken: string
    viewerEmail?: string | null
    viewerName?: string | null
    ipAddress?: string | null
    userAgent?: string | null
    viewedAt?: Date | string
  }

  export type ReportViewCreateOrConnectWithoutTenantInput = {
    where: ReportViewWhereUniqueInput
    create: XOR<ReportViewCreateWithoutTenantInput, ReportViewUncheckedCreateWithoutTenantInput>
  }

  export type ReportViewCreateManyTenantInputEnvelope = {
    data: ReportViewCreateManyTenantInput | ReportViewCreateManyTenantInput[]
    skipDuplicates?: boolean
  }

  export type TenantUserUpsertWithWhereUniqueWithoutTenantInput = {
    where: TenantUserWhereUniqueInput
    update: XOR<TenantUserUpdateWithoutTenantInput, TenantUserUncheckedUpdateWithoutTenantInput>
    create: XOR<TenantUserCreateWithoutTenantInput, TenantUserUncheckedCreateWithoutTenantInput>
  }

  export type TenantUserUpdateWithWhereUniqueWithoutTenantInput = {
    where: TenantUserWhereUniqueInput
    data: XOR<TenantUserUpdateWithoutTenantInput, TenantUserUncheckedUpdateWithoutTenantInput>
  }

  export type TenantUserUpdateManyWithWhereWithoutTenantInput = {
    where: TenantUserScalarWhereInput
    data: XOR<TenantUserUpdateManyMutationInput, TenantUserUncheckedUpdateManyWithoutTenantInput>
  }

  export type TenantUserScalarWhereInput = {
    AND?: TenantUserScalarWhereInput | TenantUserScalarWhereInput[]
    OR?: TenantUserScalarWhereInput[]
    NOT?: TenantUserScalarWhereInput | TenantUserScalarWhereInput[]
    id?: StringFilter<"TenantUser"> | string
    userId?: StringFilter<"TenantUser"> | string
    tenantId?: StringFilter<"TenantUser"> | string
    role?: EnumTenantRoleFilter<"TenantUser"> | $Enums.TenantRole
    joinedAt?: DateTimeFilter<"TenantUser"> | Date | string
  }

  export type TenantInviteUpsertWithWhereUniqueWithoutTenantInput = {
    where: TenantInviteWhereUniqueInput
    update: XOR<TenantInviteUpdateWithoutTenantInput, TenantInviteUncheckedUpdateWithoutTenantInput>
    create: XOR<TenantInviteCreateWithoutTenantInput, TenantInviteUncheckedCreateWithoutTenantInput>
  }

  export type TenantInviteUpdateWithWhereUniqueWithoutTenantInput = {
    where: TenantInviteWhereUniqueInput
    data: XOR<TenantInviteUpdateWithoutTenantInput, TenantInviteUncheckedUpdateWithoutTenantInput>
  }

  export type TenantInviteUpdateManyWithWhereWithoutTenantInput = {
    where: TenantInviteScalarWhereInput
    data: XOR<TenantInviteUpdateManyMutationInput, TenantInviteUncheckedUpdateManyWithoutTenantInput>
  }

  export type TenantInviteScalarWhereInput = {
    AND?: TenantInviteScalarWhereInput | TenantInviteScalarWhereInput[]
    OR?: TenantInviteScalarWhereInput[]
    NOT?: TenantInviteScalarWhereInput | TenantInviteScalarWhereInput[]
    id?: StringFilter<"TenantInvite"> | string
    tenantId?: StringFilter<"TenantInvite"> | string
    email?: StringFilter<"TenantInvite"> | string
    role?: EnumTenantRoleFilter<"TenantInvite"> | $Enums.TenantRole
    token?: StringFilter<"TenantInvite"> | string
    expiresAt?: DateTimeFilter<"TenantInvite"> | Date | string
    usedAt?: DateTimeNullableFilter<"TenantInvite"> | Date | string | null
    acceptedAt?: DateTimeNullableFilter<"TenantInvite"> | Date | string | null
    revokedAt?: DateTimeNullableFilter<"TenantInvite"> | Date | string | null
    createdAt?: DateTimeFilter<"TenantInvite"> | Date | string
  }

  export type AnnotationUpsertWithWhereUniqueWithoutTenantInput = {
    where: AnnotationWhereUniqueInput
    update: XOR<AnnotationUpdateWithoutTenantInput, AnnotationUncheckedUpdateWithoutTenantInput>
    create: XOR<AnnotationCreateWithoutTenantInput, AnnotationUncheckedCreateWithoutTenantInput>
  }

  export type AnnotationUpdateWithWhereUniqueWithoutTenantInput = {
    where: AnnotationWhereUniqueInput
    data: XOR<AnnotationUpdateWithoutTenantInput, AnnotationUncheckedUpdateWithoutTenantInput>
  }

  export type AnnotationUpdateManyWithWhereWithoutTenantInput = {
    where: AnnotationScalarWhereInput
    data: XOR<AnnotationUpdateManyMutationInput, AnnotationUncheckedUpdateManyWithoutTenantInput>
  }

  export type AnnotationScalarWhereInput = {
    AND?: AnnotationScalarWhereInput | AnnotationScalarWhereInput[]
    OR?: AnnotationScalarWhereInput[]
    NOT?: AnnotationScalarWhereInput | AnnotationScalarWhereInput[]
    id?: StringFilter<"Annotation"> | string
    jobId?: StringFilter<"Annotation"> | string
    tenantId?: StringFilter<"Annotation"> | string
    pageNum?: IntFilter<"Annotation"> | number
    authorId?: StringNullableFilter<"Annotation"> | string | null
    authorEmail?: StringFilter<"Annotation"> | string
    authorName?: StringNullableFilter<"Annotation"> | string | null
    fabricJson?: JsonFilter<"Annotation">
    createdAt?: DateTimeFilter<"Annotation"> | Date | string
    updatedAt?: DateTimeFilter<"Annotation"> | Date | string
  }

  export type ReportViewUpsertWithWhereUniqueWithoutTenantInput = {
    where: ReportViewWhereUniqueInput
    update: XOR<ReportViewUpdateWithoutTenantInput, ReportViewUncheckedUpdateWithoutTenantInput>
    create: XOR<ReportViewCreateWithoutTenantInput, ReportViewUncheckedCreateWithoutTenantInput>
  }

  export type ReportViewUpdateWithWhereUniqueWithoutTenantInput = {
    where: ReportViewWhereUniqueInput
    data: XOR<ReportViewUpdateWithoutTenantInput, ReportViewUncheckedUpdateWithoutTenantInput>
  }

  export type ReportViewUpdateManyWithWhereWithoutTenantInput = {
    where: ReportViewScalarWhereInput
    data: XOR<ReportViewUpdateManyMutationInput, ReportViewUncheckedUpdateManyWithoutTenantInput>
  }

  export type ReportViewScalarWhereInput = {
    AND?: ReportViewScalarWhereInput | ReportViewScalarWhereInput[]
    OR?: ReportViewScalarWhereInput[]
    NOT?: ReportViewScalarWhereInput | ReportViewScalarWhereInput[]
    id?: StringFilter<"ReportView"> | string
    jobId?: StringFilter<"ReportView"> | string
    tenantId?: StringFilter<"ReportView"> | string
    reportToken?: StringFilter<"ReportView"> | string
    viewerEmail?: StringNullableFilter<"ReportView"> | string | null
    viewerName?: StringNullableFilter<"ReportView"> | string | null
    ipAddress?: StringNullableFilter<"ReportView"> | string | null
    userAgent?: StringNullableFilter<"ReportView"> | string | null
    viewedAt?: DateTimeFilter<"ReportView"> | Date | string
  }

  export type TenantUserCreateWithoutUserInput = {
    id?: string
    role?: $Enums.TenantRole
    joinedAt?: Date | string
    tenant: TenantCreateNestedOneWithoutUsersInput
  }

  export type TenantUserUncheckedCreateWithoutUserInput = {
    id?: string
    tenantId: string
    role?: $Enums.TenantRole
    joinedAt?: Date | string
  }

  export type TenantUserCreateOrConnectWithoutUserInput = {
    where: TenantUserWhereUniqueInput
    create: XOR<TenantUserCreateWithoutUserInput, TenantUserUncheckedCreateWithoutUserInput>
  }

  export type TenantUserCreateManyUserInputEnvelope = {
    data: TenantUserCreateManyUserInput | TenantUserCreateManyUserInput[]
    skipDuplicates?: boolean
  }

  export type SessionCreateWithoutUserInput = {
    id?: string
    token: string
    expiresAt: Date | string
    createdAt?: Date | string
    ipAddress?: string | null
    userAgent?: string | null
    impersonatingTenantId?: string | null
  }

  export type SessionUncheckedCreateWithoutUserInput = {
    id?: string
    token: string
    expiresAt: Date | string
    createdAt?: Date | string
    ipAddress?: string | null
    userAgent?: string | null
    impersonatingTenantId?: string | null
  }

  export type SessionCreateOrConnectWithoutUserInput = {
    where: SessionWhereUniqueInput
    create: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput>
  }

  export type SessionCreateManyUserInputEnvelope = {
    data: SessionCreateManyUserInput | SessionCreateManyUserInput[]
    skipDuplicates?: boolean
  }

  export type MagicLinkCreateWithoutUserInput = {
    id?: string
    token: string
    pollingToken?: string | null
    code?: string | null
    ipAddress?: string | null
    expiresAt: Date | string
    usedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type MagicLinkUncheckedCreateWithoutUserInput = {
    id?: string
    token: string
    pollingToken?: string | null
    code?: string | null
    ipAddress?: string | null
    expiresAt: Date | string
    usedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type MagicLinkCreateOrConnectWithoutUserInput = {
    where: MagicLinkWhereUniqueInput
    create: XOR<MagicLinkCreateWithoutUserInput, MagicLinkUncheckedCreateWithoutUserInput>
  }

  export type MagicLinkCreateManyUserInputEnvelope = {
    data: MagicLinkCreateManyUserInput | MagicLinkCreateManyUserInput[]
    skipDuplicates?: boolean
  }

  export type TenantInviteCreateWithoutUserInput = {
    id?: string
    role?: $Enums.TenantRole
    token: string
    expiresAt: Date | string
    usedAt?: Date | string | null
    acceptedAt?: Date | string | null
    revokedAt?: Date | string | null
    createdAt?: Date | string
    tenant: TenantCreateNestedOneWithoutInvitesInput
  }

  export type TenantInviteUncheckedCreateWithoutUserInput = {
    id?: string
    tenantId: string
    role?: $Enums.TenantRole
    token: string
    expiresAt: Date | string
    usedAt?: Date | string | null
    acceptedAt?: Date | string | null
    revokedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type TenantInviteCreateOrConnectWithoutUserInput = {
    where: TenantInviteWhereUniqueInput
    create: XOR<TenantInviteCreateWithoutUserInput, TenantInviteUncheckedCreateWithoutUserInput>
  }

  export type TenantInviteCreateManyUserInputEnvelope = {
    data: TenantInviteCreateManyUserInput | TenantInviteCreateManyUserInput[]
    skipDuplicates?: boolean
  }

  export type TenantUserUpsertWithWhereUniqueWithoutUserInput = {
    where: TenantUserWhereUniqueInput
    update: XOR<TenantUserUpdateWithoutUserInput, TenantUserUncheckedUpdateWithoutUserInput>
    create: XOR<TenantUserCreateWithoutUserInput, TenantUserUncheckedCreateWithoutUserInput>
  }

  export type TenantUserUpdateWithWhereUniqueWithoutUserInput = {
    where: TenantUserWhereUniqueInput
    data: XOR<TenantUserUpdateWithoutUserInput, TenantUserUncheckedUpdateWithoutUserInput>
  }

  export type TenantUserUpdateManyWithWhereWithoutUserInput = {
    where: TenantUserScalarWhereInput
    data: XOR<TenantUserUpdateManyMutationInput, TenantUserUncheckedUpdateManyWithoutUserInput>
  }

  export type SessionUpsertWithWhereUniqueWithoutUserInput = {
    where: SessionWhereUniqueInput
    update: XOR<SessionUpdateWithoutUserInput, SessionUncheckedUpdateWithoutUserInput>
    create: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput>
  }

  export type SessionUpdateWithWhereUniqueWithoutUserInput = {
    where: SessionWhereUniqueInput
    data: XOR<SessionUpdateWithoutUserInput, SessionUncheckedUpdateWithoutUserInput>
  }

  export type SessionUpdateManyWithWhereWithoutUserInput = {
    where: SessionScalarWhereInput
    data: XOR<SessionUpdateManyMutationInput, SessionUncheckedUpdateManyWithoutUserInput>
  }

  export type SessionScalarWhereInput = {
    AND?: SessionScalarWhereInput | SessionScalarWhereInput[]
    OR?: SessionScalarWhereInput[]
    NOT?: SessionScalarWhereInput | SessionScalarWhereInput[]
    id?: StringFilter<"Session"> | string
    userId?: StringFilter<"Session"> | string
    token?: StringFilter<"Session"> | string
    expiresAt?: DateTimeFilter<"Session"> | Date | string
    createdAt?: DateTimeFilter<"Session"> | Date | string
    ipAddress?: StringNullableFilter<"Session"> | string | null
    userAgent?: StringNullableFilter<"Session"> | string | null
    impersonatingTenantId?: StringNullableFilter<"Session"> | string | null
  }

  export type MagicLinkUpsertWithWhereUniqueWithoutUserInput = {
    where: MagicLinkWhereUniqueInput
    update: XOR<MagicLinkUpdateWithoutUserInput, MagicLinkUncheckedUpdateWithoutUserInput>
    create: XOR<MagicLinkCreateWithoutUserInput, MagicLinkUncheckedCreateWithoutUserInput>
  }

  export type MagicLinkUpdateWithWhereUniqueWithoutUserInput = {
    where: MagicLinkWhereUniqueInput
    data: XOR<MagicLinkUpdateWithoutUserInput, MagicLinkUncheckedUpdateWithoutUserInput>
  }

  export type MagicLinkUpdateManyWithWhereWithoutUserInput = {
    where: MagicLinkScalarWhereInput
    data: XOR<MagicLinkUpdateManyMutationInput, MagicLinkUncheckedUpdateManyWithoutUserInput>
  }

  export type MagicLinkScalarWhereInput = {
    AND?: MagicLinkScalarWhereInput | MagicLinkScalarWhereInput[]
    OR?: MagicLinkScalarWhereInput[]
    NOT?: MagicLinkScalarWhereInput | MagicLinkScalarWhereInput[]
    id?: StringFilter<"MagicLink"> | string
    userId?: StringFilter<"MagicLink"> | string
    token?: StringFilter<"MagicLink"> | string
    pollingToken?: StringNullableFilter<"MagicLink"> | string | null
    code?: StringNullableFilter<"MagicLink"> | string | null
    ipAddress?: StringNullableFilter<"MagicLink"> | string | null
    expiresAt?: DateTimeFilter<"MagicLink"> | Date | string
    usedAt?: DateTimeNullableFilter<"MagicLink"> | Date | string | null
    createdAt?: DateTimeFilter<"MagicLink"> | Date | string
  }

  export type TenantInviteUpsertWithWhereUniqueWithoutUserInput = {
    where: TenantInviteWhereUniqueInput
    update: XOR<TenantInviteUpdateWithoutUserInput, TenantInviteUncheckedUpdateWithoutUserInput>
    create: XOR<TenantInviteCreateWithoutUserInput, TenantInviteUncheckedCreateWithoutUserInput>
  }

  export type TenantInviteUpdateWithWhereUniqueWithoutUserInput = {
    where: TenantInviteWhereUniqueInput
    data: XOR<TenantInviteUpdateWithoutUserInput, TenantInviteUncheckedUpdateWithoutUserInput>
  }

  export type TenantInviteUpdateManyWithWhereWithoutUserInput = {
    where: TenantInviteScalarWhereInput
    data: XOR<TenantInviteUpdateManyMutationInput, TenantInviteUncheckedUpdateManyWithoutUserInput>
  }

  export type UserCreateWithoutTenantsInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
    sessions?: SessionCreateNestedManyWithoutUserInput
    magicLinks?: MagicLinkCreateNestedManyWithoutUserInput
    invites?: TenantInviteCreateNestedManyWithoutUserInput
  }

  export type UserUncheckedCreateWithoutTenantsInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
    sessions?: SessionUncheckedCreateNestedManyWithoutUserInput
    magicLinks?: MagicLinkUncheckedCreateNestedManyWithoutUserInput
    invites?: TenantInviteUncheckedCreateNestedManyWithoutUserInput
  }

  export type UserCreateOrConnectWithoutTenantsInput = {
    where: UserWhereUniqueInput
    create: XOR<UserCreateWithoutTenantsInput, UserUncheckedCreateWithoutTenantsInput>
  }

  export type TenantCreateWithoutUsersInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
    invites?: TenantInviteCreateNestedManyWithoutTenantInput
    annotations?: AnnotationCreateNestedManyWithoutTenantInput
    reportViews?: ReportViewCreateNestedManyWithoutTenantInput
  }

  export type TenantUncheckedCreateWithoutUsersInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
    invites?: TenantInviteUncheckedCreateNestedManyWithoutTenantInput
    annotations?: AnnotationUncheckedCreateNestedManyWithoutTenantInput
    reportViews?: ReportViewUncheckedCreateNestedManyWithoutTenantInput
  }

  export type TenantCreateOrConnectWithoutUsersInput = {
    where: TenantWhereUniqueInput
    create: XOR<TenantCreateWithoutUsersInput, TenantUncheckedCreateWithoutUsersInput>
  }

  export type UserUpsertWithoutTenantsInput = {
    update: XOR<UserUpdateWithoutTenantsInput, UserUncheckedUpdateWithoutTenantsInput>
    create: XOR<UserCreateWithoutTenantsInput, UserUncheckedCreateWithoutTenantsInput>
    where?: UserWhereInput
  }

  export type UserUpdateToOneWithWhereWithoutTenantsInput = {
    where?: UserWhereInput
    data: XOR<UserUpdateWithoutTenantsInput, UserUncheckedUpdateWithoutTenantsInput>
  }

  export type UserUpdateWithoutTenantsInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sessions?: SessionUpdateManyWithoutUserNestedInput
    magicLinks?: MagicLinkUpdateManyWithoutUserNestedInput
    invites?: TenantInviteUpdateManyWithoutUserNestedInput
  }

  export type UserUncheckedUpdateWithoutTenantsInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sessions?: SessionUncheckedUpdateManyWithoutUserNestedInput
    magicLinks?: MagicLinkUncheckedUpdateManyWithoutUserNestedInput
    invites?: TenantInviteUncheckedUpdateManyWithoutUserNestedInput
  }

  export type TenantUpsertWithoutUsersInput = {
    update: XOR<TenantUpdateWithoutUsersInput, TenantUncheckedUpdateWithoutUsersInput>
    create: XOR<TenantCreateWithoutUsersInput, TenantUncheckedCreateWithoutUsersInput>
    where?: TenantWhereInput
  }

  export type TenantUpdateToOneWithWhereWithoutUsersInput = {
    where?: TenantWhereInput
    data: XOR<TenantUpdateWithoutUsersInput, TenantUncheckedUpdateWithoutUsersInput>
  }

  export type TenantUpdateWithoutUsersInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    invites?: TenantInviteUpdateManyWithoutTenantNestedInput
    annotations?: AnnotationUpdateManyWithoutTenantNestedInput
    reportViews?: ReportViewUpdateManyWithoutTenantNestedInput
  }

  export type TenantUncheckedUpdateWithoutUsersInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    invites?: TenantInviteUncheckedUpdateManyWithoutTenantNestedInput
    annotations?: AnnotationUncheckedUpdateManyWithoutTenantNestedInput
    reportViews?: ReportViewUncheckedUpdateManyWithoutTenantNestedInput
  }

  export type TenantCreateWithoutInvitesInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
    users?: TenantUserCreateNestedManyWithoutTenantInput
    annotations?: AnnotationCreateNestedManyWithoutTenantInput
    reportViews?: ReportViewCreateNestedManyWithoutTenantInput
  }

  export type TenantUncheckedCreateWithoutInvitesInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
    users?: TenantUserUncheckedCreateNestedManyWithoutTenantInput
    annotations?: AnnotationUncheckedCreateNestedManyWithoutTenantInput
    reportViews?: ReportViewUncheckedCreateNestedManyWithoutTenantInput
  }

  export type TenantCreateOrConnectWithoutInvitesInput = {
    where: TenantWhereUniqueInput
    create: XOR<TenantCreateWithoutInvitesInput, TenantUncheckedCreateWithoutInvitesInput>
  }

  export type UserCreateWithoutInvitesInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
    tenants?: TenantUserCreateNestedManyWithoutUserInput
    sessions?: SessionCreateNestedManyWithoutUserInput
    magicLinks?: MagicLinkCreateNestedManyWithoutUserInput
  }

  export type UserUncheckedCreateWithoutInvitesInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
    tenants?: TenantUserUncheckedCreateNestedManyWithoutUserInput
    sessions?: SessionUncheckedCreateNestedManyWithoutUserInput
    magicLinks?: MagicLinkUncheckedCreateNestedManyWithoutUserInput
  }

  export type UserCreateOrConnectWithoutInvitesInput = {
    where: UserWhereUniqueInput
    create: XOR<UserCreateWithoutInvitesInput, UserUncheckedCreateWithoutInvitesInput>
  }

  export type TenantUpsertWithoutInvitesInput = {
    update: XOR<TenantUpdateWithoutInvitesInput, TenantUncheckedUpdateWithoutInvitesInput>
    create: XOR<TenantCreateWithoutInvitesInput, TenantUncheckedCreateWithoutInvitesInput>
    where?: TenantWhereInput
  }

  export type TenantUpdateToOneWithWhereWithoutInvitesInput = {
    where?: TenantWhereInput
    data: XOR<TenantUpdateWithoutInvitesInput, TenantUncheckedUpdateWithoutInvitesInput>
  }

  export type TenantUpdateWithoutInvitesInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    users?: TenantUserUpdateManyWithoutTenantNestedInput
    annotations?: AnnotationUpdateManyWithoutTenantNestedInput
    reportViews?: ReportViewUpdateManyWithoutTenantNestedInput
  }

  export type TenantUncheckedUpdateWithoutInvitesInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    users?: TenantUserUncheckedUpdateManyWithoutTenantNestedInput
    annotations?: AnnotationUncheckedUpdateManyWithoutTenantNestedInput
    reportViews?: ReportViewUncheckedUpdateManyWithoutTenantNestedInput
  }

  export type UserUpsertWithoutInvitesInput = {
    update: XOR<UserUpdateWithoutInvitesInput, UserUncheckedUpdateWithoutInvitesInput>
    create: XOR<UserCreateWithoutInvitesInput, UserUncheckedCreateWithoutInvitesInput>
    where?: UserWhereInput
  }

  export type UserUpdateToOneWithWhereWithoutInvitesInput = {
    where?: UserWhereInput
    data: XOR<UserUpdateWithoutInvitesInput, UserUncheckedUpdateWithoutInvitesInput>
  }

  export type UserUpdateWithoutInvitesInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenants?: TenantUserUpdateManyWithoutUserNestedInput
    sessions?: SessionUpdateManyWithoutUserNestedInput
    magicLinks?: MagicLinkUpdateManyWithoutUserNestedInput
  }

  export type UserUncheckedUpdateWithoutInvitesInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenants?: TenantUserUncheckedUpdateManyWithoutUserNestedInput
    sessions?: SessionUncheckedUpdateManyWithoutUserNestedInput
    magicLinks?: MagicLinkUncheckedUpdateManyWithoutUserNestedInput
  }

  export type UserCreateWithoutSessionsInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
    tenants?: TenantUserCreateNestedManyWithoutUserInput
    magicLinks?: MagicLinkCreateNestedManyWithoutUserInput
    invites?: TenantInviteCreateNestedManyWithoutUserInput
  }

  export type UserUncheckedCreateWithoutSessionsInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
    tenants?: TenantUserUncheckedCreateNestedManyWithoutUserInput
    magicLinks?: MagicLinkUncheckedCreateNestedManyWithoutUserInput
    invites?: TenantInviteUncheckedCreateNestedManyWithoutUserInput
  }

  export type UserCreateOrConnectWithoutSessionsInput = {
    where: UserWhereUniqueInput
    create: XOR<UserCreateWithoutSessionsInput, UserUncheckedCreateWithoutSessionsInput>
  }

  export type UserUpsertWithoutSessionsInput = {
    update: XOR<UserUpdateWithoutSessionsInput, UserUncheckedUpdateWithoutSessionsInput>
    create: XOR<UserCreateWithoutSessionsInput, UserUncheckedCreateWithoutSessionsInput>
    where?: UserWhereInput
  }

  export type UserUpdateToOneWithWhereWithoutSessionsInput = {
    where?: UserWhereInput
    data: XOR<UserUpdateWithoutSessionsInput, UserUncheckedUpdateWithoutSessionsInput>
  }

  export type UserUpdateWithoutSessionsInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenants?: TenantUserUpdateManyWithoutUserNestedInput
    magicLinks?: MagicLinkUpdateManyWithoutUserNestedInput
    invites?: TenantInviteUpdateManyWithoutUserNestedInput
  }

  export type UserUncheckedUpdateWithoutSessionsInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenants?: TenantUserUncheckedUpdateManyWithoutUserNestedInput
    magicLinks?: MagicLinkUncheckedUpdateManyWithoutUserNestedInput
    invites?: TenantInviteUncheckedUpdateManyWithoutUserNestedInput
  }

  export type UserCreateWithoutMagicLinksInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
    tenants?: TenantUserCreateNestedManyWithoutUserInput
    sessions?: SessionCreateNestedManyWithoutUserInput
    invites?: TenantInviteCreateNestedManyWithoutUserInput
  }

  export type UserUncheckedCreateWithoutMagicLinksInput = {
    id?: string
    email: string
    name?: string | null
    avatarUrl?: string | null
    isSuperAdmin?: boolean
    createdAt?: Date | string
    updatedAt?: Date | string
    tenants?: TenantUserUncheckedCreateNestedManyWithoutUserInput
    sessions?: SessionUncheckedCreateNestedManyWithoutUserInput
    invites?: TenantInviteUncheckedCreateNestedManyWithoutUserInput
  }

  export type UserCreateOrConnectWithoutMagicLinksInput = {
    where: UserWhereUniqueInput
    create: XOR<UserCreateWithoutMagicLinksInput, UserUncheckedCreateWithoutMagicLinksInput>
  }

  export type UserUpsertWithoutMagicLinksInput = {
    update: XOR<UserUpdateWithoutMagicLinksInput, UserUncheckedUpdateWithoutMagicLinksInput>
    create: XOR<UserCreateWithoutMagicLinksInput, UserUncheckedCreateWithoutMagicLinksInput>
    where?: UserWhereInput
  }

  export type UserUpdateToOneWithWhereWithoutMagicLinksInput = {
    where?: UserWhereInput
    data: XOR<UserUpdateWithoutMagicLinksInput, UserUncheckedUpdateWithoutMagicLinksInput>
  }

  export type UserUpdateWithoutMagicLinksInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenants?: TenantUserUpdateManyWithoutUserNestedInput
    sessions?: SessionUpdateManyWithoutUserNestedInput
    invites?: TenantInviteUpdateManyWithoutUserNestedInput
  }

  export type UserUncheckedUpdateWithoutMagicLinksInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    name?: NullableStringFieldUpdateOperationsInput | string | null
    avatarUrl?: NullableStringFieldUpdateOperationsInput | string | null
    isSuperAdmin?: BoolFieldUpdateOperationsInput | boolean
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenants?: TenantUserUncheckedUpdateManyWithoutUserNestedInput
    sessions?: SessionUncheckedUpdateManyWithoutUserNestedInput
    invites?: TenantInviteUncheckedUpdateManyWithoutUserNestedInput
  }

  export type TenantCreateWithoutAnnotationsInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
    users?: TenantUserCreateNestedManyWithoutTenantInput
    invites?: TenantInviteCreateNestedManyWithoutTenantInput
    reportViews?: ReportViewCreateNestedManyWithoutTenantInput
  }

  export type TenantUncheckedCreateWithoutAnnotationsInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
    users?: TenantUserUncheckedCreateNestedManyWithoutTenantInput
    invites?: TenantInviteUncheckedCreateNestedManyWithoutTenantInput
    reportViews?: ReportViewUncheckedCreateNestedManyWithoutTenantInput
  }

  export type TenantCreateOrConnectWithoutAnnotationsInput = {
    where: TenantWhereUniqueInput
    create: XOR<TenantCreateWithoutAnnotationsInput, TenantUncheckedCreateWithoutAnnotationsInput>
  }

  export type TenantUpsertWithoutAnnotationsInput = {
    update: XOR<TenantUpdateWithoutAnnotationsInput, TenantUncheckedUpdateWithoutAnnotationsInput>
    create: XOR<TenantCreateWithoutAnnotationsInput, TenantUncheckedCreateWithoutAnnotationsInput>
    where?: TenantWhereInput
  }

  export type TenantUpdateToOneWithWhereWithoutAnnotationsInput = {
    where?: TenantWhereInput
    data: XOR<TenantUpdateWithoutAnnotationsInput, TenantUncheckedUpdateWithoutAnnotationsInput>
  }

  export type TenantUpdateWithoutAnnotationsInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    users?: TenantUserUpdateManyWithoutTenantNestedInput
    invites?: TenantInviteUpdateManyWithoutTenantNestedInput
    reportViews?: ReportViewUpdateManyWithoutTenantNestedInput
  }

  export type TenantUncheckedUpdateWithoutAnnotationsInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    users?: TenantUserUncheckedUpdateManyWithoutTenantNestedInput
    invites?: TenantInviteUncheckedUpdateManyWithoutTenantNestedInput
    reportViews?: ReportViewUncheckedUpdateManyWithoutTenantNestedInput
  }

  export type TenantCreateWithoutReportViewsInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
    users?: TenantUserCreateNestedManyWithoutTenantInput
    invites?: TenantInviteCreateNestedManyWithoutTenantInput
    annotations?: AnnotationCreateNestedManyWithoutTenantInput
  }

  export type TenantUncheckedCreateWithoutReportViewsInput = {
    id?: string
    name: string
    slug: string
    domain?: string | null
    engineTenantId?: string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: $Enums.TenantStatus
    createdAt?: Date | string
    updatedAt?: Date | string
    users?: TenantUserUncheckedCreateNestedManyWithoutTenantInput
    invites?: TenantInviteUncheckedCreateNestedManyWithoutTenantInput
    annotations?: AnnotationUncheckedCreateNestedManyWithoutTenantInput
  }

  export type TenantCreateOrConnectWithoutReportViewsInput = {
    where: TenantWhereUniqueInput
    create: XOR<TenantCreateWithoutReportViewsInput, TenantUncheckedCreateWithoutReportViewsInput>
  }

  export type TenantUpsertWithoutReportViewsInput = {
    update: XOR<TenantUpdateWithoutReportViewsInput, TenantUncheckedUpdateWithoutReportViewsInput>
    create: XOR<TenantCreateWithoutReportViewsInput, TenantUncheckedCreateWithoutReportViewsInput>
    where?: TenantWhereInput
  }

  export type TenantUpdateToOneWithWhereWithoutReportViewsInput = {
    where?: TenantWhereInput
    data: XOR<TenantUpdateWithoutReportViewsInput, TenantUncheckedUpdateWithoutReportViewsInput>
  }

  export type TenantUpdateWithoutReportViewsInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    users?: TenantUserUpdateManyWithoutTenantNestedInput
    invites?: TenantInviteUpdateManyWithoutTenantNestedInput
    annotations?: AnnotationUpdateManyWithoutTenantNestedInput
  }

  export type TenantUncheckedUpdateWithoutReportViewsInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    domain?: NullableStringFieldUpdateOperationsInput | string | null
    engineTenantId?: NullableStringFieldUpdateOperationsInput | string | null
    settings?: JsonNullValueInput | InputJsonValue
    status?: EnumTenantStatusFieldUpdateOperationsInput | $Enums.TenantStatus
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    users?: TenantUserUncheckedUpdateManyWithoutTenantNestedInput
    invites?: TenantInviteUncheckedUpdateManyWithoutTenantNestedInput
    annotations?: AnnotationUncheckedUpdateManyWithoutTenantNestedInput
  }

  export type TenantUserCreateManyTenantInput = {
    id?: string
    userId: string
    role?: $Enums.TenantRole
    joinedAt?: Date | string
  }

  export type TenantInviteCreateManyTenantInput = {
    id?: string
    email: string
    role?: $Enums.TenantRole
    token: string
    expiresAt: Date | string
    usedAt?: Date | string | null
    acceptedAt?: Date | string | null
    revokedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type AnnotationCreateManyTenantInput = {
    id?: string
    jobId: string
    pageNum: number
    authorId?: string | null
    authorEmail: string
    authorName?: string | null
    fabricJson: JsonNullValueInput | InputJsonValue
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type ReportViewCreateManyTenantInput = {
    id?: string
    jobId: string
    reportToken: string
    viewerEmail?: string | null
    viewerName?: string | null
    ipAddress?: string | null
    userAgent?: string | null
    viewedAt?: Date | string
  }

  export type TenantUserUpdateWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    joinedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    user?: UserUpdateOneRequiredWithoutTenantsNestedInput
  }

  export type TenantUserUncheckedUpdateWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    joinedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantUserUncheckedUpdateManyWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    joinedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantInviteUpdateWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    acceptedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    revokedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    user?: UserUpdateOneRequiredWithoutInvitesNestedInput
  }

  export type TenantInviteUncheckedUpdateWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    acceptedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    revokedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantInviteUncheckedUpdateManyWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    acceptedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    revokedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AnnotationUpdateWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    pageNum?: IntFieldUpdateOperationsInput | number
    authorId?: NullableStringFieldUpdateOperationsInput | string | null
    authorEmail?: StringFieldUpdateOperationsInput | string
    authorName?: NullableStringFieldUpdateOperationsInput | string | null
    fabricJson?: JsonNullValueInput | InputJsonValue
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AnnotationUncheckedUpdateWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    pageNum?: IntFieldUpdateOperationsInput | number
    authorId?: NullableStringFieldUpdateOperationsInput | string | null
    authorEmail?: StringFieldUpdateOperationsInput | string
    authorName?: NullableStringFieldUpdateOperationsInput | string | null
    fabricJson?: JsonNullValueInput | InputJsonValue
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AnnotationUncheckedUpdateManyWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    pageNum?: IntFieldUpdateOperationsInput | number
    authorId?: NullableStringFieldUpdateOperationsInput | string | null
    authorEmail?: StringFieldUpdateOperationsInput | string
    authorName?: NullableStringFieldUpdateOperationsInput | string | null
    fabricJson?: JsonNullValueInput | InputJsonValue
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type ReportViewUpdateWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    reportToken?: StringFieldUpdateOperationsInput | string
    viewerEmail?: NullableStringFieldUpdateOperationsInput | string | null
    viewerName?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    viewedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type ReportViewUncheckedUpdateWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    reportToken?: StringFieldUpdateOperationsInput | string
    viewerEmail?: NullableStringFieldUpdateOperationsInput | string | null
    viewerName?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    viewedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type ReportViewUncheckedUpdateManyWithoutTenantInput = {
    id?: StringFieldUpdateOperationsInput | string
    jobId?: StringFieldUpdateOperationsInput | string
    reportToken?: StringFieldUpdateOperationsInput | string
    viewerEmail?: NullableStringFieldUpdateOperationsInput | string | null
    viewerName?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    viewedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantUserCreateManyUserInput = {
    id?: string
    tenantId: string
    role?: $Enums.TenantRole
    joinedAt?: Date | string
  }

  export type SessionCreateManyUserInput = {
    id?: string
    token: string
    expiresAt: Date | string
    createdAt?: Date | string
    ipAddress?: string | null
    userAgent?: string | null
    impersonatingTenantId?: string | null
  }

  export type MagicLinkCreateManyUserInput = {
    id?: string
    token: string
    pollingToken?: string | null
    code?: string | null
    ipAddress?: string | null
    expiresAt: Date | string
    usedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type TenantInviteCreateManyUserInput = {
    id?: string
    tenantId: string
    role?: $Enums.TenantRole
    token: string
    expiresAt: Date | string
    usedAt?: Date | string | null
    acceptedAt?: Date | string | null
    revokedAt?: Date | string | null
    createdAt?: Date | string
  }

  export type TenantUserUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    joinedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenant?: TenantUpdateOneRequiredWithoutUsersNestedInput
  }

  export type TenantUserUncheckedUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    joinedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantUserUncheckedUpdateManyWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    joinedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type SessionUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    impersonatingTenantId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type SessionUncheckedUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    impersonatingTenantId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type SessionUncheckedUpdateManyWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    userAgent?: NullableStringFieldUpdateOperationsInput | string | null
    impersonatingTenantId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type MagicLinkUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    pollingToken?: NullableStringFieldUpdateOperationsInput | string | null
    code?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type MagicLinkUncheckedUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    pollingToken?: NullableStringFieldUpdateOperationsInput | string | null
    code?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type MagicLinkUncheckedUpdateManyWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    pollingToken?: NullableStringFieldUpdateOperationsInput | string | null
    code?: NullableStringFieldUpdateOperationsInput | string | null
    ipAddress?: NullableStringFieldUpdateOperationsInput | string | null
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantInviteUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    acceptedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    revokedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    tenant?: TenantUpdateOneRequiredWithoutInvitesNestedInput
  }

  export type TenantInviteUncheckedUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    acceptedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    revokedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TenantInviteUncheckedUpdateManyWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    tenantId?: StringFieldUpdateOperationsInput | string
    role?: EnumTenantRoleFieldUpdateOperationsInput | $Enums.TenantRole
    token?: StringFieldUpdateOperationsInput | string
    expiresAt?: DateTimeFieldUpdateOperationsInput | Date | string
    usedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    acceptedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    revokedAt?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }



  /**
   * Batch Payload for updateMany & deleteMany & createMany
   */

  export type BatchPayload = {
    count: number
  }

  /**
   * DMMF
   */
  export const dmmf: runtime.BaseDMMF
}